import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

from ..models.task import Task
from ..exceptions import ParsingError


class CommandParser:
    WAKE_WORDS = [
        "окей календарь",
        "слушай календарь",
        "привет календарь",
        "календарь",
        "ассистент",
    ]
    SLEEP_WORDS = ["стоп", "хватит", "фон", "пауза", "выключись"]
    EXIT_WORDS = ["выход", "закрыть", "пока", "до свидания", "завершение"]
    SHOW_WORDS = ["покажи", "список", "что на", "что у", "какие задачи"]
    HELP_WORDS = ["помощь", "команды", "что умеешь", "справка"]
    CLEAR_WORDS = ["очисти", "удали все", "стереть"]

    TRIGGER_WORDS = [
        "поставь",
        "запиши",
        "добавь",
        "напомни",
        "создай",
        "поставить",
        "записать",
        "добавить",
        "напомнить",
        "создать",
        "внеси",
        "внести",
        "запланируй",
        "запланировать",
    ]
    TASK_KEYWORDS = [
        "задачу",
        "задание",
        "напоминание",
        "встречу",
        "дело",
        "событие",
        "мероприятие",
        "звонок",
        "совещание",
    ]

    WEEKDAYS_RU: Dict[str, int] = {
        "понедельник": 0,
        "вторник": 1,
        "среду": 2,
        "среда": 2,
        "четверг": 3,
        "пятницу": 4,
        "пятница": 4,
        "субботу": 5,
        "суббота": 5,
        "воскресенье": 6,
        "воскресение": 6,
    }
    MONTHS_RU: Dict[str, int] = {
        "января": 1,
        "февраля": 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12,
    }
    PRIORITY_KEYWORDS: Dict[str, int] = {
        "срочно": 2,
        "важно": 2,
        "высокий": 2,
        "средний": 1,
        "обычный": 0,
        "низкий": 0,
    }

    @property
    def _months_re(self) -> str:
        return "(?:" + "|".join(self.MONTHS_RU) + ")"

    @property
    def _weekdays_re(self) -> str:
        return "(?:" + "|".join(self.WEEKDAYS_RU) + ")"

    def parse(self, text: str) -> Optional[Task]:
        text = text.lower().strip()

        if not self._is_command(text):
            return None

        try:
            date = self._extract_date(text)
            if date is None:
                return None
            h, m = self._extract_time(text)
            date = date.replace(hour=h, minute=m, second=0, microsecond=0)
            title = self._extract_title(text)
            if not title:
                return None
            priority = self._extract_priority(text)
            task = Task(
                title=title,
                date=date,
                priority=priority,
            )
            return task

        except Exception as e:
            raise ParsingError(f"Ошибка при парсинге команды: {e}")

    def get_command_type(self, text: str) -> str:
        t = text.lower().strip()
        if any(w in t for w in self.WAKE_WORDS):
            return "wake"
        if any(w in t.split() for w in self.EXIT_WORDS):
            return "exit"
        if any(w in t.split() for w in self.SLEEP_WORDS):
            return "sleep"
        if any(w in t for w in self.SHOW_WORDS):
            return "show"
        if any(w in t for w in self.HELP_WORDS):
            return "help"
        if any(w in t for w in self.CLEAR_WORDS):
            return "clear"
        return "add"

    def _is_command(self, text: str) -> bool:
        return any(word in text for word in self.TRIGGER_WORDS)

    def _extract_date(self, text: str) -> Optional[datetime]:
        now = datetime.now()
        if "послезавтра" in text:
            return now + timedelta(days=2)
        if "завтра" in text:
            return now + timedelta(days=1)
        if "сегодня" in text:
            return now
        for name, wd in self.WEEKDAYS_RU.items():
            if name in text.split():
                return now + timedelta(days=(wd - now.weekday()) % 7 or 7)
        m = re.search(rf"(\d{{1,2}})[\s\-]?(?:го|ого)?\s+{self._months_re}", text)
        if m:
            d, mo = int(m.group(1)), self.MONTHS_RU[m.group(2)]
            try:
                return datetime(now.year if mo >= now.month else now.year + 1, mo, d)
            except ValueError:
                pass
        return None

    def _extract_time(self, text: str) -> Tuple[int, int]:
        match = re.search(r"в\s+(\d{1,2})[:\-](\d{2})", text)
        if match:
            return int(match.group(1)), int(match.group(2))

        match = re.search(r"в\s+(\d{1,2})(?:\s+(?:час|часов|часа))?", text)
        if match:
            return int(match.group(1)), 0

        if "полдень" in text:
            return 12, 0
        if "полночь" in text:
            return 0, 0

        return 9, 0

    def _extract_title(self, text: str) -> Optional[str]:
        stop = self.TRIGGER_WORDS + self.TASK_KEYWORDS + ["мне", "на", "пожалуйста"]
        words = [w for w in text.split() if w not in stop]
        cleaned = " ".join(words)
        for w in self.PRIORITY_KEYWORDS:
            cleaned = cleaned.replace(w, "")
        for p in [
            rf"\d{{1,2}}[\s\-]?(?:го|ого)?\s+{self._months_re}",
            r"в\s+\d{1,2}[:\-]\d{2}",
            r"в\s+\d{1,2}(?:\s+(?:час|часов|часа))?",
            r"(?:сегодня|завтра|послезавтра)",
            self._weekdays_re,
        ]:
            cleaned = re.sub(p, " ", cleaned)
        t = " ".join(cleaned.split()).strip().strip(".,!?;:")
        return t[0].upper() + t[1:] if t else None

    def _extract_priority(self, text: str) -> int:
        for word, priority in self.PRIORITY_KEYWORDS.items():
            if word in text.split():
                return priority
        return 0
