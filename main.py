# main.py
from core.login_system import LoginSystem
from core.voice_engine import VoiceEngine
from core.task_manager import TaskManager
from gui.main_window import JarvisGUI

if __name__ == "__main__":
    login = LoginSystem()
    username = login.run()  # Returns username if login successful

    if username:
        print(f"[LOGIN SUCCESS] Logged in as: {username}")
        voice_engine = VoiceEngine()
        task_manager = TaskManager(user_name=username)
        gui = JarvisGUI(voice_engine, task_manager, username=username, auto_listen=True)
        gui.run()
    else:
        print("[LOGIN FAILED] Exiting Jarvis securely.")
