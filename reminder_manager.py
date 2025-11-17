# core/reminder_manager.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from plyer import notification

class ReminderManager:
    def __init__(self, voice_engine=None):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.voice_engine = voice_engine

    def set_reminder(self, task, minutes):
        run_time = datetime.now() + timedelta(minutes=minutes)
        self.scheduler.add_job(self._notify, 'date', run_date=run_time, args=[task])
        return f"Reminder set for {task} in {minutes} minutes."

    def _notify(self, task):
        # 🔔 Show popup
        notification.notify(
            title='Jarvis Reminder',
            message=task,
            timeout=10
        )
        # 🗣️ Speak it too
        if self.voice_engine:
            self.voice_engine.speak(f"Reminder: {task}")
