import logging
import re
import sys

from datetime import datetime, timedelta
from typing import Optional

from src.config import Config
from src.models.task import Task
from src.storage.base import BaseCalendarStorage
from src.storage.json_storage import JsonCalendarStorage

# from parser.command_parser import CommandParser
# from speech.recognizer import VoiceRecognizer
# from speech.synthesizer import SpeechSynthesizer
from src.exceptions import VoiceCalendarError, ConfigurationError

logger = logging.getLogger(__name__)


class MockParser:
    """
    Mock объект для имитации работы парсера
    """

    def parse(self, text: str) -> Optional[Task]:
        text_lower = text.lower().strip()
        now = datetime.now()
        if "послезавтра" in text_lower:
            date = now + timedelta(days=2)
        if "завтра" in text_lower:
            date = now + timedelta(days=1)
        else:
            date = now

        hour, minute = 9, 0
        match = re.search(r"в\s+(\d{1,2})[:\-](\d{2})", text)
        if match:
            hour, minute = (int(match.group(1)), int(match.group(2)))
        else:
            match = re.search(r"в\s+(\d{1,2})", text)
            if match:
                hour = int(match.group(1))
        date = date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        stop_words = [
            "поставь",
            "запиши",
            "добавь",
            "напомни",
            "создай",
            "задачу",
            "задание",
            "напоминание",
            "встречу",
            "дело",
            "мне",
            "на",
            "пожалуйста",
        ]

        title = text_lower
        for word in stop_words:
            title = title.replace(word, " ")

        title = re.sub(r"в\s+\d{1,2}[:\-]?\d{0,2}", " ", title)
        title = re.sub(r"(сегодня|завтра|послезавтра)", " ", title)

        title = " ".join(title.split()).strip()
        if not title:
            return None

        title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        return Task(title=title, date=date)

    def parse_query_date(self, text) -> Optional[datetime]:
        text_lower = text.lower().strip()
        if "сегодня" in text_lower:
            return datetime.now()
        elif "завтра" in text_lower:
            return datetime.now() + timedelta(days=1)
        return None


class MockRecognizer:
    def listen_safe(self) -> Optional[str]:
        try:
            return input("\n Введите команду: ")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt


class MockSynthesizer:
    def speak(self, text) -> None:
        print(f"{text}")


class VoiceCalendarApp:
    HELP_TEXT = ""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.config.validate()
        self.storage = JsonCalendarStorage(self.config.storage_path)

        self.parser = MockParser()
        self.recognizer = MockRecognizer()
        self.synthesizer = MockSynthesizer()

        self._running = False
        self._commands_history = []

    def run(self):
        self._running = True
        self.synthesizer.speak("Голосовой помощник готов. Чем могу помочь?")
        print(self.HELP_TEXT)
        while self._running:
            try:
                text = self.recognizer.listen_safe()
                if text is None:
                    continue
                print(f"\n Распознано: {text}")
                self._commands_history.append(text)
                self._handle_command(text)
            except KeyboardInterrupt:
                print("Завершение работы...")
                self.stop()
                sys.exit(0)

    def stop(self):
        self._running = False

    def _handle_command(self, text):
        text_lower = text.lower().strip()
        if any(w in text_lower for w in ["выход", "стоп", "закрыть"]):
            self._cmd_exit()
        elif any(w in text_lower for w in ["покажи", "список", "что на"]):
            self._cmd_show_tasks(text)
        elif any(w in text_lower for w in ["помощь", "команды"]):
            self._cmd_help()
        elif "статус" in text_lower:
            self._cmd_status()
        elif any(w in text for w in ["очисти", "удали все", "очистить"]):
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
        query_date = self.parser.parse_query_date(text)
        if query_date:
            tasks = self.storage.get_tasks_for_date(query_date)
            label = f"Задачи на {query_date.strftime('%d.%m.%Y')}"
        elif "сегодня" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now())
            label = "Задачи на сегодня"
        elif "завтра" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now() + timedelta(days=1))
            label = "Задачи на завтра"
        else:
            tasks = self.storage.get_upcoming_tasks(days=7)
            label = "Задачи на неделю"
        if not tasks:
            self.synthesizer.speak("Задач не найдено")
            return
        print(f"\n{label}")
        for task in tasks:
            print(f" - {task}")
        self.synthesizer.speak(f"Найдено {len(tasks)} задач")

    def _cmd_help(self):
        print(self.HELP_TEXT)
        print("Смотрите список задач на экране")

    def _cmd_clear_tasks(self) -> None:
        """Очищает все задачи."""
        self.storage.clear_all()
        self.synthesizer.speak("Все задачи удалены.")

    def _cmd_status(self):
        count = self.storage.get_task_count()
        self.synthesizer.speak(f"В хранилище {count} задач")

    def _cmd_exit(self):
        self.synthesizer.speak("До свидания!")
        self.stop()


if __name__ == "__main__":
    app = VoiceCalendarApp()
    app.run()
