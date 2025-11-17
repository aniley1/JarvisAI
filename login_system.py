# core/login_system.py
import os
import json
import cv2
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import customtkinter as ctk
from tkinter import messagebox

# =============================
# 📂 PATH SETUP
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "user_data.json")
INTRUDER_DIR = os.path.join(BASE_DIR, "../assets/intruder_photos")
os.makedirs(INTRUDER_DIR, exist_ok=True)

# =============================
# ✉️ EMAIL CONFIG
# =============================
SENDER_EMAIL = "arnavsingh022001@gmail.com"
SENDER_PASS = "zzka zmww sqhh fpin"  # Gmail app password
AUTHOR_EMAIL = "arnavsingh022001@gmail.com"  # You receive alerts here

# =============================
# 📧 EMAIL UTILITIES
# =============================
def send_email(recipient, subject, message, image_path=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img:
                msg.attach(MIMEImage(img.read(), name=os.path.basename(image_path)))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)

        print(f"[EMAIL SENT] To: {recipient}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

# =============================
# 🧠 DATA UTILITIES
# =============================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =============================
# 📸 CAMERA CAPTURE
# =============================
def capture_intruder(username):
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("[CAMERA ERROR] Cannot access webcam.")
        return None
    ret, frame = cam.read()
    if ret:
        image_path = os.path.join(INTRUDER_DIR, f"intruder_{username}.jpg")
        cv2.imwrite(image_path, frame)
        cam.release()
        cv2.destroyAllWindows()
        return image_path
    cam.release()
    cv2.destroyAllWindows()
    return None

# =============================
# 🧩 MAIN CLASS: LOGIN SYSTEM
# =============================
class LoginSystem:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("Jarvis Secure Access")
        self.app.geometry("400x420")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.users = load_data()
        self.authenticated_user = None  # ✅ store logged in username

        self.title = ctk.CTkLabel(self.app, text="🧠 Jarvis Secure Portal", font=("Arial", 22, "bold"))
        self.title.pack(pady=20)

        self.username_entry = ctk.CTkEntry(self.app, placeholder_text="Username")
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self.app, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=10)

        self.private_key_entry = ctk.CTkEntry(self.app, placeholder_text="Private Key", show="*")
        self.private_key_entry.pack(pady=10)

        self.email_entry = ctk.CTkEntry(self.app, placeholder_text="Email (for register only)")
        self.email_entry.pack(pady=10)

        self.login_btn = ctk.CTkButton(self.app, text="Login", command=self.login_user)
        self.login_btn.pack(pady=10)

        self.register_btn = ctk.CTkButton(self.app, text="Register", command=self.register_user)
        self.register_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(self.app, text="")
        self.status_label.pack(pady=10)

    # =============================
    # 👤 REGISTER USER
    # =============================
    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        private_key = self.private_key_entry.get().strip()
        email = self.email_entry.get().strip()

        if not username or not password or not private_key or not email:
            messagebox.showwarning("Missing Info", "All fields are required for registration!")
            return

        if username in self.users:
            messagebox.showerror("Error", "Username already exists!")
            return

        self.users[username] = {
            "password": password,
            "private_key": private_key,
            "email": email
        }

        save_data(self.users)
        messagebox.showinfo("Success", f"User '{username}' registered successfully!")

        send_email(
            email,
            subject="✅ Jarvis Registration Successful",
            message=f"Hello {username},\n\nYour Jarvis account has been successfully registered!\nWelcome aboard!"
        )

    # =============================
    # 🔑 LOGIN USER
    # =============================
    def login_user(self):
        username = self.username_entry.get().strip()
        private_key = self.private_key_entry.get().strip()

        if username not in self.users:
            self.status_label.configure(text="User not found.")
            intruder_img = capture_intruder(username)
            send_email(
                AUTHOR_EMAIL,
                "🚨 Unauthorized Access Alert",
                f"Unknown user '{username}' tried to log into Jarvis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
                image_path=intruder_img
            )
            return

        if self.users[username]["private_key"] == private_key:
            self.authenticated_user = username  # ✅ store username
            self.app.destroy()
        else:
            self.status_label.configure(text="Unauthorized access attempt!")
            intruder_img = capture_intruder(username)
            send_email(
                AUTHOR_EMAIL,
                "🚨 Unauthorized Access Attempt",
                f"Someone tried to log in as '{username}' with an invalid key at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
                image_path=intruder_img
            )

    def run(self):
        """Run GUI and return username if authenticated."""
        self.app.mainloop()
        return self.authenticated_user
