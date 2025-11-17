import os, smtplib
from email.mime.text import MIMEText

sender = os.getenv("JARVIS_EMAIL")
password = os.getenv("JARVIS_EMAIL_PASS")
server = os.getenv("JARVIS_SMTP_SERVER", "smtp.gmail.com")
port = int(os.getenv("JARVIS_SMTP_PORT", "465"))
recipient = sender  # send to yourself

msg = MIMEText("Hello from Jarvis! This is a test email.")
msg["Subject"] = "Jarvis Email Test"
msg["From"] = sender
msg["To"] = recipient

try:
    with smtplib.SMTP_SSL(server, port, timeout=15) as s:
        s.login(sender, password)
        s.send_message(msg)
    print("Email sent successfully! Check your inbox.")
except Exception as e:
    print("Email sending failed:", e)
