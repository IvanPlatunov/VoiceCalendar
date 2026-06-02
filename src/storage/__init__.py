"""Модули хранилища VoiceCalendar."""

from src.storage.base import BaseCalendarStorage
from src.storage.json_storage import JsonCalendarStorage

__all__ = [
    "BaseCalendarStorage",
    "JsonCalendarStorage",
]

# GoogleCalendarStorage импортируется опционально
try:
    from src.storage.gc_storage import GoogleCalendarStorage

    __all__.append("GoogleCalendarStorage")
except ImportError:
    pass
