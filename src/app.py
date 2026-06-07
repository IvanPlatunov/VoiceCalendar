import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from .config import Config
from .storage.json_storage import JsonCalendarStorage
from .parser.command_parser import CommandParser
from .speech.recognizer import VoiceRecognizer, RecognizerEvent
from .speech.synthesizer import SpeechSynthesizer


class VoiceCalendarApp:
    HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║                   🗓️  VOICE CALENDAR — СПРАВКА                   ║
╠══════════════════════════════════════════════════════════════════╣
║  🔔 АКТИВАЦИЯ                                                    ║
║    • "Привет, календарь" / "Календарь" / "Ассистент"             ║
║                                                                  ║
║  📝 ДОБАВЛЕНИЕ                                                   ║
║    • "Поставь задачу [что] на [когда] в [время]"                 ║
║    • Приоритет: "срочно", "важно"                                ║
║                                                                  ║
║  📋 ПРОСМОТР                                                     ║
║    • "Покажи задачи на сегодня" / "Что у меня на завтра"         ║
║                                                                  ║
║  😴 РЕЖИМЫ                                                       ║
║    • "Стоп", "фон" — фоновый режим                               ║
║    • "Выход" — завершить работу                                  ║
║    • "Помощь" — эта справка                                      ║
║    • "Очисти всё" — удалить все задачи                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.config.validate()
        self.storage = JsonCalendarStorage(self.config.storage_path)

        self.parser = CommandParser()
        self.recognizer = VoiceRecognizer(self.config)
        self.synthesizer = SpeechSynthesizer(
            rate=self.config.speech_rate,
            volume=self.config.speech_volume,
            language="ru",
        )

    def run(self):
        print("=" * 60)
        print("  🗓️  VoiceCalendar")
        print("Голосовой помощник для управления задачами")
        print("=" * 60)
        self._running = True
        self.synthesizer.speak("Голосовой помощник готов. Чем могу помочь?")
        print(self.HELP_TEXT)
        try:
            while True:
                event, text = self.recognizer.listen_safe()
                if event == RecognizerEvent.WAKE:
                    self.synthesizer.speak("Слушаю!")
                    continue
                elif event == RecognizerEvent.SLEEP:
                    self.synthesizer.speak("Ухожу в фон")
                if text is None:
                    continue
                print(f"\n🗣️ Распознано: {text}")
                self._handle_command(text)
                time.sleep(0.5)
                self.synthesizer.speak("Слушаю!")
        except SystemExit:
            self.synthesizer.speak("До свидания!")
            print("Завершение работы...")
            sys.exit(0)

    def _handle_command(self, text):
        cmd = self.parser.get_command_type(text)

        if cmd == "exit":
            raise SystemExit(0)
        elif cmd == "sleep":
            return
        elif cmd == "show":
            self._cmd_show_tasks(text)
        elif cmd == "help":
            self._cmd_help()
        elif cmd == "clear":
            self._cmd_clear_tasks()
        else:
            self._cmd_add_task(text)

    def _cmd_add_task(self, text):
        task = self.parser.parse(text)
        if task:
            self.storage.add_task(task)
            date_str = task.date.strftime("%d %B в %H:%M")
            self.synthesizer.speak(f"Задача [{task.title}] записана на {date_str}")
        else:
            self.synthesizer.speak("Не удалось распознать задачу")

    def _cmd_show_tasks(self, text):
        query_date = self.parser._extract_date(text)
        if query_date:
            tasks = self.storage.get_tasks_for_date(query_date)
            label = f" 📅 Задачи на {query_date.strftime('%d.%m.%Y')}"
        elif "сегодня" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now())
            label = " 📅 Задачи на сегодня"
        elif "завтра" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now() + timedelta(days=1))
            label = " 📅 Задачи на завтра"
        else:
            tasks = self.storage.get_upcoming_tasks(days=7)
            label = " 📅 Задачи на неделю"
        if not tasks:
            self.synthesizer.speak("Задач не найдено")
            return
        print(f"\n{label}")
        for task in tasks:
            print(f" - {task}")
        self.synthesizer.speak(f"Найдено {len(tasks)} задач")

    def _cmd_help(self):
        print("Смотрите список команд на экране")
        print(self.HELP_TEXT)
        self.synthesizer.speak("Смотрите список команд на экране.")

    def _cmd_clear_tasks(self) -> None:
        """Очищает все задачи."""
        self.storage.clear_all()
        self.synthesizer.speak("Все задачи удалены")


if __name__ == "__main__":
    app = VoiceCalendarApp()
    app.run()
