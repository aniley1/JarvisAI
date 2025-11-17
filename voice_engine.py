from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import os

class VoiceEngine:
    def __init__(self):
        # Make sure ffmpeg is set properly
        os.environ["PATH"] += os.pathsep + os.path.abspath("C:/Users/Lenovo/Downloads/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin")
        
        # Set the path to the audio file
        self.output_path = os.path.join("core", "voice_output.mp3")

    def speak(self, text):
        try:
            # Convert text to speech
            tts = gTTS(text=text, lang='en')
            tts.save(self.output_path)

            # Load and play audio using pydub
            audio = AudioSegment.from_file(self.output_path, format="mp3")
            play(audio)

        except Exception as e:
            print(f"Error speaking: {e}")

    def output(self, text):
        print(f"Jarvis: {text}")
        self.speak(text)

    def listen(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.pause_threshold = 1
            audio = recognizer.listen(source)

        try:
            print("Recognizing...")
            command = recognizer.recognize_google(audio, language='en-in')
            print(f"You said: {command}")
        except sr.UnknownValueError:
            self.output("Sorry, I didn't catch that. Please say again.")
            return ""
        except sr.RequestError:
            self.output("Sorry, I can't access the speech service right now.")
            return ""

        return command.lower()
