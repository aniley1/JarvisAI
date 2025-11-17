# gui/main_window.py
import sys
import os
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from core.voice_engine import VoiceEngine
from core.task_manager import TaskManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class JarvisGUI:
    def __init__(self, voice_engine, task_manager, username, auto_listen=True):
        self.voice_engine = voice_engine
        self.task_manager = task_manager
        self.username = username
        self.auto_listen = auto_listen

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.app = ctk.CTk()
        self.app.title(f"Jarvis AI Assistant - {self.username}")
        self.app.geometry("700x600")
        self.app.resizable(False, False)

        self.title_label = ctk.CTkLabel(
            self.app, text="🧠 Jarvis AI Assistant", font=("Arial", 28, "bold"), text_color="cyan"
        )
        self.title_label.pack(pady=10)

        self.avatar_path = os.path.join(PROJECT_ROOT, "gui", "assets", "jarvis.png")
        if os.path.exists(self.avatar_path):
            image = Image.open(self.avatar_path).resize((100, 100))
            self.avatar_img = ImageTk.PhotoImage(image)
            self.avatar_label = ctk.CTkLabel(self.app, image=self.avatar_img, text="")
            self.avatar_label.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.app, text="Status: Idle", font=("Arial", 16), text_color="lightgrey")
        self.status_label.pack(pady=2)

        self.log_box = ctk.CTkTextbox(self.app, width=620, height=300, font=("Consolas", 14), wrap="word")
        self.log_box.pack(pady=10)
        self.log_box.configure(state="disabled")

        self.listen_button = ctk.CTkButton(
            self.app, text="🎤 Talk to Jarvis", font=("Arial", 18), width=200, height=40, command=self.start_jarvis
        )
        self.listen_button.pack(pady=20)

        # ✅ Personalized greeting
        self.output(f"Hello {self.username}! How can I help you today?")

        if self.auto_listen:
            threading.Thread(target=self.run_jarvis, daemon=True).start()

    def append_log(self, text, speaker="Jarvis"):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{speaker}: {text}\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def output(self, text):
        self.append_log(text, speaker="Jarvis")
        threading.Thread(target=self.voice_engine.output, args=(text,), daemon=True).start()

    def start_jarvis(self):
        threading.Thread(target=self.run_jarvis, daemon=True).start()

    def run_jarvis(self):
        self.status_label.configure(text="Status: Listening...")
        if (command := self.voice_engine.listen()):
            self.append_log(command, speaker=self.username)
            self.status_label.configure(text="Status: Processing...")
            self.task_manager.execute(command, self)
        else:
            self.output("I couldn't hear you. Please try again.")
        self.status_label.configure(text="Status: Idle")

    def run(self):
        self.app.mainloop()
