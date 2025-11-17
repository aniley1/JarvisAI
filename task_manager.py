# core/task_manager.py
"""
Comprehensive TaskManager for Jarvis desktop assistant.
Features:
 - Web/apps control (open/close Chrome, YouTube, open websites)
 - Math (safe_eval)
 - Memory: remember <key> is <value> / recall via "do you remember" or "what is"
 - Reminders (uses core.reminder_manager if present)
 - Vision (face/QR) if core.vision_manager present
 - Dynamic weather (OpenWeatherMap) and news (NewsAPI)
 - Volume control via pycaw (optional)
 - Wake-word listener (speech_recognition optional), integrated with GUI
 - Persistent sleep/awake state persisted in core/jarvis_state.json
 - Graceful degradation when optional libs are missing
"""

import os
import webbrowser
import subprocess
import datetime
import ast
import psutil
import ctypes
import screen_brightness_control as sbc
import json
import wikipedia
import re
import requests
import threading
import time
import traceback
import contextlib

# Optional modules
try:
    import pyjokes
except Exception:
    pyjokes = None

# pycaw for Windows volume control (optional)
_USE_PYCAW = False
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    _USE_PYCAW = True
except Exception:
    AudioUtilities = None
    IAudioEndpointVolume = None
    cast = None
    POINTER = None
    CLSCTX_ALL = None

# speech_recognition for wake listener (optional)
try:
    import speech_recognition as sr
    _HAS_SPEECH_RECOG = True
except Exception:
    sr = None
    _HAS_SPEECH_RECOG = False

# ------------------ API KEYS (replace with your keys) ------------------
WEATHER_API_KEY = "b240a14304741a2e7ac1a966ed1d789a"   # replace if needed
NEWS_API_KEY = "8cd53f8952d44ae0b41f09c1d7ddffcc"      # replace if needed

# ------------------ Paths ------------------
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(CORE_DIR, "memory.json")
SLEEP_STATE_PATH = os.path.join(CORE_DIR, "jarvis_state.json")


class TaskManager:
    def __init__(self, user_name="User", start_wake_listener=False):
        """Initialize managers and optional features."""
        self.user_name = user_name
        # volume interface (pycaw)
        if _USE_PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume = cast(interface, POINTER(IAudioEndpointVolume))
            except Exception:
                self.volume = None
                print("[TaskManager] Warning: pycaw initialization failed.")
        else:
            self.volume = None

        # optional managers (imported lazily)
        try:
            from core.reminder_manager import ReminderManager
            self.reminder_manager = ReminderManager()
        except Exception:
            self.reminder_manager = None
            print("[TaskManager] ReminderManager not available.")

        try:
            from core.vision_manager import VisionManager
            self.vision = VisionManager()
        except Exception:
            self.vision = None
            print("[TaskManager] VisionManager not available.")

        # wake-listener thread control
        self._wake_thread = None
        self._wake_thread_stop = threading.Event()
        self.jarvis_gui = None  # set with set_jarvis_gui()

        # persistent sleep/awake state (True => assistant sleeping)
        self.sleep_mode = self._load_sleep_state()

        # If requested, start wake listener in background
        if start_wake_listener and _HAS_SPEECH_RECOG:
            # user should still call set_jarvis_gui afterwards
            threading.Thread(target=self.start_wake_listener, daemon=True).start()

    # -------------------- Persistence helpers --------------------
    def _load_sleep_state(self):
        try:
            if os.path.exists(SLEEP_STATE_PATH):
                with open(SLEEP_STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("sleep_mode", False))
        except Exception:
            print("[TaskManager] Failed to load sleep state:", traceback.format_exc())
        return False

    def _save_sleep_state(self):
        try:
            with open(SLEEP_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"sleep_mode": bool(self.sleep_mode)}, f, indent=2)
        except Exception:
            print("[TaskManager] Failed to save sleep state:", traceback.format_exc())

    def load_memory(self):
        try:
            if os.path.exists(MEMORY_PATH):
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            print("[TaskManager] Failed to load memory:", traceback.format_exc())
        return {}

    def save_memory(self, data):
        try:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            print("[TaskManager] Failed to save memory:", traceback.format_exc())

    # -------------------- Wake listener integration --------------------
    def set_jarvis_gui(self, jarvis_gui):
        """Give TaskManager a reference to the GUI instance (JarvisGUI)."""
        self.jarvis_gui = jarvis_gui

    def start_wake_listener(self, jarvis_gui=None):
        """
        Start background wake listener that listens for wake phrases.
        Provide jarvis_gui if available; it will be stored.
        """
        if not _HAS_SPEECH_RECOG:
            print("[WakeListener] speech_recognition not installed; wake listener disabled.")
            return

        if jarvis_gui is not None:
            self.set_jarvis_gui(jarvis_gui)

        if self._wake_thread and self._wake_thread.is_alive():
            print("[WakeListener] Already running.")
            return

        self._wake_thread_stop.clear()
        self._wake_thread = threading.Thread(target=self._wake_listener_loop, daemon=True)
        self._wake_thread.start()
        print("[WakeListener] Started.")

    def stop_wake_listener(self):
        if self._wake_thread:
            self._wake_thread_stop.set()
            self._wake_thread = None
            print("[WakeListener] Stop requested.")

    def _wake_listener_loop(self):
        """Loop using SpeechRecognition to detect wake word and call GUI or execute flow."""
        try:
            recognizer = sr.Recognizer()
            mic = sr.Microphone()
        except Exception as e:
            print("[WakeListener] Microphone or SpeechRecognition not available:", e)
            return

        # calibrate once
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
        except Exception as e:
            print("[WakeListener] Microphone access failed:", e)
            return

        wake_phrases = ("wake up jarvis", "wake up", "wake jarvis", "jarvis wake up", "hey jarvis", "jarvis")
        print("[WakeListener] Listening for wake words...")

        while not self._wake_thread_stop.is_set():
            try:
                with mic as source:
                    audio = recognizer.listen(source, phrase_time_limit=5, timeout=6)
                try:
                    text = recognizer.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    time.sleep(2)
                    continue

                # If any wake phrase appears:
                if any(p in text for p in wake_phrases):
                    print("[WakeListener] Detected:", text)
                    try:
                        # If we have a GUI, wake it and trigger its listening loop
                        if self.jarvis_gui:
                            # If assistant sleeping and it's a wake phrase: wake assistant
                            if self.sleep_mode:
                                self.sleep_mode = False
                                self._save_sleep_state()
                                with contextlib.suppress(Exception):
                                    self.jarvis_gui.output("I'm back. How can I help you?")
                            # start GUI listening thread (safe to call repeatedly)
                            with contextlib.suppress(Exception):
                                self.jarvis_gui.start_jarvis()
                            # also trigger a friendly fallback greeting
                            with contextlib.suppress(Exception):
                                self.execute("hey jarvis", self.jarvis_gui)
                        else:
                            # No GUI: execute hello in console mode
                            with contextlib.suppress(Exception):
                                self.execute("hey jarvis", None)
                    except Exception as e:
                        print("[WakeListener] Error triggering Jarvis:", e)
                time.sleep(0.2)
            except Exception:
                # don't crash the wake thread
                traceback.print_exc()
                time.sleep(1)

    # -------------------- Main command dispatcher --------------------
    def execute(self, command, gui):
        """
        Main dispatcher:
         - command: raw string (will be lowercased/stripped)
         - jarvis: JarvisGUI instance (preferred) or None (console mode)
        """
        if not command:
            return

        command = command.lower().strip()

        def reply(text):
            """Unified reply helper. Sends to GUI if present, else prints."""
            try:
                if gui and hasattr(gui, "output"):
                    gui.output(text)
                else:
                    print("Jarvis:", text)
            except Exception:
                print("Jarvis:", text)

        # ---------------- Sleep/Wake management (top priority) ----------------
        assistant_sleep_keywords = ("go to sleep", "sleep jarvis", "put jarvis to sleep", "jarvis go to sleep", "sleep now jarvis")
        wake_keywords = ("wake up jarvis", "wake up", "wake jarvis", "jarvis wake up", "hey jarvis", "jarvis")

        # If explicit assistant sleep command
        if any(kw in command for kw in assistant_sleep_keywords):
            try:
                self.sleep_mode = True
                self._save_sleep_state()
                # whisperable message (TTS engine may not support whisper but this is a UX cue)
                reply("Going to sleep. Say 'wake up Jarvis' to wake me.")
            except Exception:
                reply("Could not enter sleep mode.")
            return

        # If explicit wake command
        if any(kw in command for kw in wake_keywords):
            # If sleeping, wake and stop here
            if self.sleep_mode:
                self.sleep_mode = False
                self._save_sleep_state()
                reply("I'm back. How can I help you?")
                return
            # If awake and a pure greeting:
            if command in ["hey jarvis", "jarvis"]:
                gui.output(f"Hello {self.user_name}, I’m listening.")
                return

            
        # otherwise let the command fall through to normal handling

        # If sleeping and not a wake command: ignore
        if self.sleep_mode:
            reply("I am sleeping. Say 'wake up Jarvis' to activate me.")
            return

        # ----------------- Personal / identity queries -----------------
        if "who are you" in command or "what is your name" in command or command.startswith("your name") :
            reply("I am Jarvis, your personal AI assistant. I can open apps, fetch news and weather, set reminders, and more.")
            return

        if "who am i" in command or "what is my name" in command:
            # try to find a stored 'name' in memory
            memory = self.load_memory()
            found_name = None
            # check common keys
            for k, v in memory.items():
                if "name" in k.lower() or "my name" in k.lower() or k.lower().strip() in ("name", "myname", "username"):
                    found_name = v
                    break
                # if value contains a likely name and key contains 'me' or similar
                if isinstance(v, str) and v.lower().strip() in ("{self.user_name}",):  # user had Arnav earlier
                    found_name = v
                    break
            if found_name:
                reply(f"You are {found_name}.")
            else:
                reply("I don't know your name yet. Tell me by saying 'remember my name is <your name>'.")
            return

        # ----------------- Remember / Memory -----------------
        if command.startswith("remember"):
            try:
                statement = command.replace("remember", "", 1).strip()
                if " is " in statement:
                    key, value = statement.split(" is ", 1)
                    memory = self.load_memory()
                    memory[key.strip()] = value.strip()
                    self.save_memory(memory)
                    reply(f"Got it. I will remember that {key.strip()} is {value.strip()}.")
                else:
                    # store as 'note_<timestamp>'
                    memory = self.load_memory()
                    stamp = f"note_{int(time.time())}"
                    memory[stamp] = statement
                    self.save_memory(memory)
                    reply("Okay, I've remembered that.")
            except Exception:
                reply("I couldn't remember that properly.")
            return

        # Ask about memory: "do you remember ..." or "what is <key>"
        if "do you remember" in command or command.startswith("what is") or command .startswith("who is"):
            memory = self.load_memory()
            found = False
            for key, value in memory.items():
                if key.lower() in command or (isinstance(value, str) and value.lower() in command):
                    reply(f"Yes. {key} is {value}.")
                    found = True
                    break
            if not found:
                reply("I don't remember that.")
            return

        # ----------------- Weather -----------------
        if "weather in" in command or command.startswith("weather "):
            try:
                if "weather in" in command:
                    city = command.split("weather in", 1)[1].strip()
                else:
                    city = command.replace("weather", "", 1).strip()
                if not city:
                    reply("Which city do you want the weather for?")
                    return
                self._get_weather(city, reply)
            except Exception:
                reply("Weather check failed.")
            return

        # ----------------- News -----------------
        if command.startswith("news in") or command.startswith("news about") or command == "news":
            try:
                if command == "news":
                    self._get_news(None, reply)
                elif command.startswith("news in"):
                    topic = command.split("news in", 1)[1].strip()
                    self._get_news(topic or None, reply)
                else:
                    topic = command.split("news about", 1)[1].strip()
                    self._get_news(topic or None, reply)
            except Exception:
                reply("News search failed.")
            return

        # ----------------- YouTube / Browser -----------------
        if "open youtube and play" in command:
            try:
                song = command.split("open youtube and play", 1)[1].strip()
                query = requests.utils.quote(song)
                url = f"https://www.youtube.com/results?search_query={query}"
                webbrowser.open(url)
                reply(f"Searching YouTube for {song}.")
            except Exception:
                reply("Couldn't play the song.")
            return

        if "open youtube" in command:
            webbrowser.open("https://www.youtube.com")
            reply("Opening YouTube.")
            return

        # Chrome searches
        if ("open chrome and search about" in command) or ("search in chrome" in command) or ("search about" in command and "chrome" in command):
            try:
                topic = ""
                if "open chrome and search about" in command:
                    topic = command.split("open chrome and search about", 1)[1].strip()
                elif "search in chrome" in command:
                    topic = command.split("search in chrome", 1)[1].strip()
                elif "search about" in command:
                    topic = command.split("search about", 1)[1].strip()
                if not topic:
                    reply("What would you like me to search for?")
                    return
                query = requests.utils.quote(topic)
                chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                target = f"https://www.google.com/search?q={query}"
                if os.path.exists(chrome_path):
                    subprocess.Popen([chrome_path, target])
                else:
                    webbrowser.open(target)
                reply(f"Searching for {topic}.")
            except Exception:
                reply("Couldn't perform the search.")
            return

        # Close Chrome/YouTube
        if "close chrome" in command:
            try:
                os.system("taskkill /f /im chrome.exe")
                reply("Closed Google Chrome.")
            except Exception:
                reply("Couldn't close Chrome.")
            return

        if "close youtube" in command:
            try:
                os.system("taskkill /f /im chrome.exe")
                reply("Closed YouTube.")
            except Exception:
                reply("Couldn't close YouTube.")
            return

        # ----------------- Quick links -----------------
        if "open google" in command:
            webbrowser.open("https://www.google.com")
            reply("Opening Google.")
            return
        if "open github" in command:
            webbrowser.open("https://www.github.com")
            reply("Opening GitHub.")
            return

        # ----------------- Local apps -----------------
        if "open notepad" in command:
            try:
                subprocess.Popen(["notepad.exe"])
                reply("Opening Notepad.")
            except Exception:
                reply("Couldn't open Notepad.")
            return

        if "open calculator" in command:
            try:
                subprocess.Popen(["calc.exe"])
                reply("Opening Calculator.")
            except Exception:
                reply("Couldn't open Calculator.")
            return

        if "open command prompt" in command or command == "open cmd":
            try:
                subprocess.Popen(["cmd.exe"])
                reply("Opening Command Prompt.")
            except Exception:
                reply("Couldn't open Command Prompt.")
            return

        if command == "open chrome":
            try:
                chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                if os.path.exists(chrome_path):
                    subprocess.Popen([chrome_path])
                else:
                    webbrowser.open("https://www.google.com")
                reply("Opening Google Chrome.")
            except Exception:
                reply("Couldn't open Chrome.")
            return

        # ----------------- Time / Battery -----------------
        if "time" in command and all(op not in command for op in ["calculate", "plus", "minus", "divide", "into", "multiplied"]):
            now = datetime.datetime.now().strftime("%I:%M %p")
            reply(f"The time is {now}.")
            return

        if "battery" in command:
            try:
                battery = psutil.sensors_battery()
                if battery:
                    percent = battery.percent
                    charging = battery.power_plugged
                    status = "charging" if charging else "not charging"
                    reply(f"Battery is at {percent}% and it is {status}.")
                else:
                    reply("Battery info not available.")
            except Exception:
                reply("Could not get battery info.")
            return

        # ----------------- Math -----------------
        math_keywords = ("calculate", "what is", "what's")
        if any(k in command for k in math_keywords) and any(op in command for op in ["plus", "minus", "into", "multiplied", "divide", "divided", "+", "-", "*", "/"]):
            try:
                expression = command
                for token in ("calculate", "what is", "what's"):
                    expression = expression.replace(token, "")
                expression = expression.strip()
                expression = expression.replace("plus", "+").replace("minus", "-")
                expression = expression.replace("into", "*").replace("multiplied by", "*").replace("multiplied", "*")
                expression = expression.replace("divide by", "/").replace("divided by", "/").replace("divide", "/").replace("divided", "/")
                # safe eval
                result = self.safe_eval(expression)
                if result != "Error":
                    reply(f"The result is {result}")
                else:
                    reply("Sorry, I couldn’t calculate that.")
            except Exception:
                reply("Sorry, I couldn't calculate that.")
            return

        # ----------------- Volume -----------------
        if "volume up" in command and self.volume:
            try:
                current = self.volume.GetMasterVolumeLevelScalar()
                self.volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
                reply("Volume increased.")
            except Exception:
                reply("Could not change volume.")
            return

        if "volume down" in command and self.volume:
            try:
                current = self.volume.GetMasterVolumeLevelScalar()
                self.volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
                reply("Volume decreased.")
            except Exception:
                reply("Could not change volume.")
            return

        if "mute" in command:
            try:
                if self.volume:
                    self.volume.SetMute(1, None)
                    reply("Muted.")
                else:
                    reply("Mute not supported.")
            except Exception:
                reply("Could not change mute status.")
            return

        if "unmute" in command:
            try:
                if self.volume:
                    self.volume.SetMute(0, None)
                    reply("Unmuted.")
                else:
                    reply("Unmute not supported.")
            except Exception:
                reply("Could not change mute status.")
            return

        # ----------------- System controls -----------------
        if "shutdown" in command:
            reply("Shutting down system.")
            with contextlib.suppress(Exception):
                os.system("shutdown /s /t 1")
            return

        if "restart" in command:
            reply("Restarting system.")
            with contextlib.suppress(Exception):
                os.system("shutdown /r /t 1")
            return

        # system sleep (explicit system-level sleep)
        if "put system to sleep" in command or ("system" in command and "sleep" in command):
            reply("Putting system to sleep.")
            with contextlib.suppress(Exception):
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return

        if "lock" in command:
            reply("Locking computer.")
            with contextlib.suppress(Exception):
                ctypes.windll.user32.LockWorkStation()
            return

        # ----------------- Brightness -----------------
        if "brightness" in command:
            try:
                if "increase" in command:
                    sbc.set_brightness("+10")
                    reply("Increasing brightness.")
                elif "decrease" in command:
                    sbc.set_brightness("-10")
                    reply("Decreasing brightness.")
                elif "set brightness to" in command:
                    val = int(command.split("set brightness to")[-1].strip().replace("%", ""))
                    sbc.set_brightness(val)
                    reply(f"Setting brightness to {val} percent.")
                else:
                    reply("Specify increase, decrease, or set brightness to <value>.")
            except Exception:
                reply("Brightness adjustment failed.")
            return

        # ----------------- Wikipedia (info) -----------------
        # NOTE: handle "who is" after we've handled "who are you" / identity
        if command.startswith("who is ") or command.startswith("what is "):
            try:
                topic = command.replace("who is", "").replace("what is", "").strip()
                if not topic:
                    reply("Please be more specific.")
                    return
                # simple protection: avoid one-word ambiguous queries e.g., 'Jarvis'
                if len(topic.split()) == 1:
                    # but if user asked for 'who is jarvis' we still do wiki
                    pass
                summary = wikipedia.summary(topic, sentences=2)
                reply(summary)
            except Exception:
                reply("Sorry, I couldn't find information on that.")
            return

        # ----------------- Reminders -----------------
        if "remind me" in command:
            try:
                match = re.search(r"remind me to (.+?) in (\d+) minute", command)
                if match and self.reminder_manager:
                    task = match.group(1)
                    minutes = int(match.group(2))
                    # if GUI available provide voice engine to reminders
                    if gui and hasattr(gui, "voice_engine"):
                        self.reminder_manager.voice_engine = gui.voice_engine
                    response = self.reminder_manager.set_reminder(task, minutes)
                    reply(response)
                else:
                    reply("Say something like 'remind me to call mom in 10 minutes'.")
            except Exception:
                reply("Could not set the reminder.")
            return

        # ----------------- Vision (face, QR) -----------------
        if "detect face" in command or "scan face" in command:
            if self.vision:
                reply("Starting face detection.")
                try:
                    self.vision.detect_faces()
                except Exception:
                    reply("Face detection failed.")
            else:
                reply("Face detection module not available.")
            return

        if "scan qr" in command or "read qr code" in command:
            if self.vision:
                reply("Opening QR code scanner.")
                try:
                    self.vision.detect_qr()
                except Exception:
                    reply("QR scanning failed.")
            else:
                reply("QR scanner module not available.")
            return

        # ----------------- Jokes -----------------
        if "joke" in command:
            if pyjokes:
                try:
                    reply(pyjokes.get_joke())
                except Exception:
                    reply("Couldn't get a joke right now.")
            else:
                reply("I don't have the jokes module installed.")
            return

        # ----------------- NLP fallback -----------------
        if gui and hasattr(gui, "nlp") and hasattr(gui.nlp, "generate_response"):
            try:
                resp = gui.nlp.generate_response(command)
                reply(resp)
            except Exception:
                reply("I couldn't understand that.")
            return

        # final fallback
        reply("Sorry, I don't understand that.")

    # -------------------- Helpers --------------------
    def safe_eval(self, expr):
        """Safely evaluate arithmetic expressions using AST whitelist."""
        try:
            node = ast.parse(expr, mode='eval')
            for subnode in ast.walk(node):
                if not isinstance(subnode, (ast.Expression, ast.BinOp, ast.UnaryOp,
                                            ast.Constant, ast.Load, ast.Add, ast.Sub,
                                            ast.Mult, ast.Div, ast.Pow, ast.Mod,
                                            ast.FloorDiv, ast.Constant, ast.UAdd, ast.USub)):
                    raise ValueError("Unsafe expression")
            return eval(compile(node, filename="<ast>", mode="eval"))
        except Exception:
            return "Error"

    def _get_weather(self, city, reply_fn):
        """Fetch current weather for a city and call reply_fn with a string."""
        try:
            if not WEATHER_API_KEY:
                reply_fn("Weather API key not set.")
                return
            city_q = city.strip()
            url = f"http://api.openweathermap.org/data/2.5/weather?q={requests.utils.quote(city_q)}&appid={WEATHER_API_KEY}&units=metric"
            resp = requests.get(url, timeout=8)
            data = resp.json()
            if data.get("cod") in (200, "200"):
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                reply_fn(f"The weather in {city_q} is {desc} with temperature {temp}°C.")
            else:
                reply_fn("Couldn't fetch weather. Check the city name.")
        except Exception:
            reply_fn("Error retrieving weather.")

    def _get_news(self, topic, reply_fn):
        """Fetch top news for a topic or top headlines if topic is None."""
        try:
            if not NEWS_API_KEY:
                reply_fn("News API key not set.")
                return
            if topic:
                q = requests.utils.quote(topic)
                url = f"https://newsapi.org/v2/everything?q={q}&apiKey={NEWS_API_KEY}&pageSize=3"
            else:
                url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}&pageSize=3"
            resp = requests.get(url, timeout=8)
            data = resp.json()
            if data.get("status") == "ok":
                articles = data.get("articles", [])[:3]
                if not articles:
                    reply_fn("No news found.")
                    return
                for idx, art in enumerate(articles, start=1):
                    title = art.get("title", "No title")
                    reply_fn(f"Headline {idx}: {title}")
            else:
                reply_fn("Couldn't fetch news at the moment.")
        except Exception:
            reply_fn("Error retrieving news.")
