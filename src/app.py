import logging
import re

from datetime import datetime, timedelta
from typing import Optional

from src.config import Config
from src.models.task import Task
from src.storage.base import BaseCalendarStorage
from src.storage.json_storage import JsonCalendarStorage

# from src.parser.command_parser import CommandParser
# from src.speech.recognizer import VoiceRecognizer
# from src.speech.synthesizer import SpeechSynthesizer
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
            hour, minute = int(match.group(1), match.group(2))
        else:
            match = re.search(r"в\s+(\d{1,2})")
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

    def parse_query_date(slef, text) -> Optional[datetime]:
        text_lower = text.lower().strip()
        if "сегодня" in text_lower:
            return datetime.now()
        elif "завтра" in text_lower:
            return datetime.now() + timedelta(days=1)
        return None


class MockRecognizer:
    def listen_safe(self) -> Optional[str]:
        try:
            return input("\n Введите команду")
        except (EOFError, KeyboardInterrupt):
            return None


class MockSynthesizer:
    def speak(self, text) -> None:
        print(f"{text}")
