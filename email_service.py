# core/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import socket
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ------------------------------------------------------------------
# ⚙️ CONFIGURATION (EDIT THESE VALUES)
# ------------------------------------------------------------------

# Use a Gmail account (you must enable “App Passwords” if 2FA is on)
SENDER_EMAIL = "arnavsingh022001@gmail.com"
SENDER_PASSWORD = "zzka zmww sqhh fpin"

# Default subject prefixes
APP_NAME = "Jarvis AI Assistant"

# ------------------------------------------------------------------
# 🧠 CORE MAIL FUNCTIONS
# ------------------------------------------------------------------

def send_email(receiver_email, subject, body):
    """Generic reusable email sender."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = f"{APP_NAME} - {subject}"

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[EMAIL SERVICE] ✅ Email sent to {receiver_email}")
        return True

    except Exception as e:
        print(f"[EMAIL SERVICE] ❌ Failed to send email: {e}")
        return False

# ------------------------------------------------------------------
# 📩 TEMPLATES
# ------------------------------------------------------------------

def send_registration_email(receiver_email, username):
    """Welcome email after successful registration."""
    body = f"""
Hi {username},

Welcome to {APP_NAME}!

Your registration was successful.
You can now log in using your password, voice, and face authentication.

Stay secure and productive,
- Your Jarvis AI Assistant 🤖
"""
    send_email(receiver_email, "Welcome to Jarvis!", body)


def send_unauthorized_alert(receiver_email):
    """Alert when unauthorized person tries to access."""
    ip_address = socket.gethostbyname(socket.gethostname())
    body = f"""
⚠️ SECURITY ALERT ⚠️

An unauthorized access attempt was detected on your Jarvis AI system.

Details:
    • Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    • Machine: {socket.gethostname()}
    • IP Address: {ip_address}

If this wasn’t you, please check your system immediately.

Stay safe,
Jarvis AI Security Team 🛡️
"""
    send_email(receiver_email, "Unauthorized Access Attempt Detected", body)


def send_login_notification(receiver_email, username):
    """Notify when successful login occurs."""
    ip_address = socket.gethostbyname(socket.gethostname())
    body = f"""
Hi {username},

Login successful to {APP_NAME}.

Details:
    • Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    • Machine: {socket.gethostname()}
    • IP Address: {ip_address}

If this was not you, please reset your credentials immediately.

- Jarvis Security
"""
    send_email(receiver_email, "Login Successful", body)
