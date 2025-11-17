# core/wake_listener.py
"""
Robust wake listener for Jarvis.

- Auto-detects the main Jarvis script (main.py or gui/main_window.py) relative to this file,
  or you can set JARVIS_MAIN_SCRIPT to an absolute path.
- Uses gTTS + playsound for greetings (make sure gTTS & playsound installed).
- Attempts to use pythonw.exe to launch Jarvis without a console window (if available).
- Keeps persistent state in jarvis_state.json (active/sleep).
"""

import speech_recognition as sr
import json
import os
import time
import subprocess
import sys
from datetime import datetime
from gtts import gTTS
import playsound
import threading
import contextlib

# If you want, hardcode your jarvis entrypoint here:
# Example: r"C:\Users\Lenovo\OneDrive\Desktop\JarvisAI\main.py"
JARVIS_MAIN_SCRIPT = "C:\\Users\\Lenovo\\OneDrive\\Desktop\\JarvisAI\\core"

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_state.json")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_launcher.pid")


def tts_speak(text, slow=False):
    """Speak text using gTTS and playsound (synchronous)."""
    try:
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_wake.mp3")
        tts = gTTS(text=text, lang="en", slow=slow)
        tts.save(tmp)
        playsound.playsound(tmp)
        with contextlib.suppress(Exception):
            os.remove(tmp)
    except Exception as e:
        print("[WakeListener] TTS error:", e)


def load_state():
    """Return True if active, False if sleeping. Default active."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("active", True))
    except Exception as e:
        print("[WakeListener] load_state error:", e)
    return True


def save_state(active: bool):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"active": active}, f, indent=2)
    except Exception as e:
        print("[WakeListener] save_state error:", e)


def find_jarvis_main():
    """Try to automatically find your Jarvis main script if JARVIS_MAIN_SCRIPT is None."""
    if JARVIS_MAIN_SCRIPT and os.path.exists(JARVIS_MAIN_SCRIPT):
        return os.path.abspath(JARVIS_MAIN_SCRIPT)

    # search relative to this file (repo root)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(base, "main.py"),
        os.path.join(base, "gui", "main_window.py"),
        os.path.join(base, "run.py"),
    ]
    return next((os.path.abspath(p) for p in candidates if os.path.exists(p)), None)


def already_running():
    """Basic check: look for pid file and whether process is alive."""
    with contextlib.suppress(Exception):
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            # cross-platform minimal check
            if pid and pid != os.getpid():
                # try to see if process exists
                with contextlib.suppress(Exception):
                    os.kill(pid, 0)
                    return True
                # process not running
                return False
    return False


def write_pid(pid):
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(pid))
    except Exception as e:
        print("[WakeListener] write_pid error:", e)


def remove_pid():
    with contextlib.suppress(Exception):
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def launch_jarvis():
    """Launch the Jarvis main script using pythonw (if available) to avoid console popups."""
    main_script = find_jarvis_main()
    if not main_script:
        print("[WakeListener] Could not find Jarvis main script. Update JARVIS_MAIN_SCRIPT.")
        return False

    # choose pythonw if available for a hidden window
    python_exe = sys.executable
    pythonw = None
    if python_exe.lower().endswith("python.exe"):
        candidate = python_exe[:-len("python.exe")] + "pythonw.exe"
        if os.path.exists(candidate):
            pythonw = candidate

    exe_to_use = pythonw or python_exe

    # If jarvis
    if already_running():
        print("[WakeListener] Jarvis appears to be already running (pid file).")
        return True

    try:
        # Launch detached process
        if os.name == "nt":
            # On windows use CREATE_NEW_PROCESS_GROUP to detach
            proc = subprocess.Popen([exe_to_use, main_script], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            proc = subprocess.Popen([exe_to_use, main_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

        write_pid(proc.pid)
        print(f"[WakeListener] Launched Jarvis PID={proc.pid} script={main_script}")
        return True
    except Exception as e:
        print("[WakeListener] Failed to launch Jarvis:", e)
        return False


def stop_jarvis_process():
    """Attempt to stop previously-launched Jarvis (if pid file exists)."""
    with contextlib.suppress(Exception):
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            # try terminate
            if pid:
                with contextlib.suppress(Exception):
                    if os.name == "nt":
                        subprocess.Popen(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.kill(pid, 9)
            remove_pid()


def listen_loop():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    active = load_state()
    print(f"[WakeListener] Started. Active={active}")

    # small warmup
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, phrase_time_limit=5)

            try:
                text = recognizer.recognize_google(audio).lower()
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                print("[WakeListener] speech service unavailable, retrying...")
                time.sleep(2)
                continue

            print("[Heard]", text)

            # Sleep command for assistant
            if any(phrase in text for phrase in ["go to sleep jarvis", "sleep jarvis", "jarvis go to sleep", "sleep now jarvis"]):
                if active:
                    tts_speak("Going to sleep.", slow=True)
                    active = False
                    save_state(active)
                    print("[WakeListener] Assistant set to sleep.")
                else:
                    print("[WakeListener] Already sleeping.")
                continue

            # Wake commands
            if any(phrase in text for phrase in ["wake up jarvis", "hey jarvis", "wake jarvis", "jarvis wake up", "hello jarvis"]):
                if not active:
                    # waking from sleep
                    tts_speak("I'm back.", slow=True)
                    active = True
                    save_state(active)
                else:
                    # normal greeting
                    # say a short greeting asynchronously (so we don't block recognition for long)
                    greeting = get_time_greeting()
                    threading.Thread(target=tts_speak, args=(greeting,), daemon=True).start()

                # Launch Jarvis if not running
                if (launched := launch_jarvis()):
                    # small pause to allow GUI to initialize
                    time.sleep(2)
                continue

            # If active and not a wake/sleep command we do nothing here — the GUI's voice engine will handle subsequent commands
        except KeyboardInterrupt:
            print("[WakeListener] KeyboardInterrupt, exiting.")
            break
        except Exception as e:
            print("[WakeListener] Error in listen loop:", e)
            time.sleep(1)


def get_time_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning Arnav. I am here."
    elif 12 <= hour < 18:
        return "Good afternoon Arnav. I am here."
    else:
        return "Good evening Arnav. I am here."


if __name__ == "__main__":
    listen_loop()
