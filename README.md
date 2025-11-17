# Jarvis AI Desktop Assistant

**Jarvis** is a voice-enabled, secure, Python-based desktop assistant that automates system tasks, retrieves information, and provides a personalized experience for each user.

---

## 🚀 Features

- **Secure Login & Registration**  
  Users register with a username, password, private key, and email.  
  On login, only the correct private key grants access.

- **Intruder Detection & Alerts**  
  If a login attempt fails (wrong key or unknown username), Jarvis captures a photo using the webcam and sends a security alert to the admin’s email.

- **Voice Interaction**  
  Jarvis listens to your voice commands, converts speech to text, and speaks back using text-to-speech.

- **Task Execution**  
  Execute system-level commands like opening apps, controlling brightness, volume, shutting down, etc.

- **Information Fetching**  
  - Current **Weather** via OpenWeatherMap API  
  - Latest **News** via NewsAPI  
  - **Wikipedia** queries for general knowledge  

- **Memory**  
  Jarvis can remember facts (e.g., “remember my name is Prerna”) and recall them later.

- **Wake-Word Support**  
  Activate Jarvis using voice phrases like “Hey Jarvis”.

- **Personalized Greeting**  
  On login, Jarvis greets the user by their username (“Hello Prerna!”).

---

## 🧪 Technology Stack

- **Language**: Python  
- **GUI**: CustomTkinter  
- **Voice Input/Output**: SpeechRecognition, gTTS, playsound  
- **Computer Vision**: OpenCV (for intruder photo)  
- **Email Alerts**: smtplib  
- **APIs**: OpenWeatherMap, NewsAPI  
- **Data Storage**: JSON (`user_data.json`, `memory.json`)  
- **Concurrency**: Python threading  

---
JarvisAI/
│
├── main.py
├── core/
│ ├── login_system.py
│ ├── task_manager.py
│ ├── voice_engine.py
│ └── ...
│
├── gui/
│ ├── main_window.py
│ └── assets/
│ └── jarvis.png
│
├── user_data.json
├── memory.json
└── README.md


---

## 💻 Installation & Setup

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/jarvis-ai-assistant.git  
   cd jarvis-ai-assistant  


Install dependencies
Make sure you have Python 3.9+ installed, then run:

pip install -r requirements.txt  


Configure Email

Open core/login_system.py

Replace SENDER_EMAIL and SENDER_PASS with your Gmail address + App Password

Replace AUTHOR_EMAIL with your admin email for alert notifications

Run Jarvis

python main.py  

🎯 Usage

On launch, register a new user if you don’t already have one.

Then log in with your private key.

Once logged in, Jarvis GUI opens — use the “🎤 Talk to Jarvis” button or say “Hey Jarvis”.

Give commands like:

“Open Notepad”

“What’s the weather in Mumbai?”

“Tell me the news about space”

“Remember my name is Prerna”

Jarvis will respond via voice and display the responses in the GUI.

🔐 Security & Privacy

Credentials (username, private keys, email) are stored in a local JSON file (user_data.json) — not shared externally.

Intruder images are captured only when a login fails and stored locally.

Email alerts for unauthorized access are sent to a preset admin email.

✅ Future Enhancements

Face recognition for login instead of private key

Calendar and email integration

Multi-language voice support

Cloud-based storage for user data to sync across devices

Mobile companion app

📚 References

Python Documentation – https://docs.python.org/3

CustomTkinter – https://github.com/TomSchimansky/CustomTkinter

OpenWeatherMap API – https://openweathermap.org/api

NewsAPI – https://newsapi.org

SpeechRecognition Python library – https://pypi.org/project/SpeechRecognition

gTTS (Google Text to Speech) – https://pypi.org/project/gTTS

🤝 Contributing

Feel free to open issues or pull requests if you want to suggest improvements or new features.

🧑‍💼 Author

Arnav Kumar — Creator of Jarvis AI Desktop Assistant.
Prerna Uthale  -- Developer of Jarvis AI GUI.
## 📁 Project Structure

