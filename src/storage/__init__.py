"""Модули хранилища VoiceCalendar."""

from storage.base import BaseCalendarStorage
from storage.json_storage import JsonCalendarStorage

__all__ = [
    "BaseCalendarStorage",
    "JsonCalendarStorage",
]

# GoogleCalendarStorage импортируется опционально
try:
    from src.storage.google_calendar_storage import GoogleCalendarStorage

    __all__.append("GoogleCalendarStorage")
except ImportError:
    pass

