import os

print("JARVIS_EMAIL:", os.getenv("JARVIS_EMAIL"))
print("JARVIS_SMTP_SERVER:", os.getenv("JARVIS_SMTP_SERVER"))
print("JARVIS_SMTP_PORT:", os.getenv("JARVIS_SMTP_PORT"))
print("Password Set?", bool(os.getenv("JARVIS_EMAIL_PASS")))
