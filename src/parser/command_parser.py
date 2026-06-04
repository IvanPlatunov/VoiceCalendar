import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging

from models.task import Task
from exceptions import ParsingError

logger = logging.getLogger(__name__)


class CommandParser:
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
        "срочный": 2,
        "срочную": 2,
        "важно": 2,
        "важный": 2,
        "важную": 2,
        "важное": 2,
        "высокий": 2,
        "высоким": 2,
        "высокую": 2,
        "средний": 1,
        "средним": 1,
        "среднюю": 1,
        "обычный": 0,
        "обычным": 0,
        "обычную": 0,
        "низкий": 0,
        "низким": 0,
        "низкую": 0,
    }

    DURATION_PATTERNS: list = [
        (r"на\s+(\d+)\s+минут", 1),
        (r"на\s+(\d+)\s+час", 60),
        (r"на\s+(\d+)\s+полтора\s+часа", 90),
        (r"длительностью\s+(\d+)\s+минут", 1),
        (r"длительностью\s+(\d+)\s+час", 60),
    ]

    def parse(self, text: str) -> Optional[Task]:
        text = text.lower().strip()
        logger.debug(f"Парсинг текста: '{text}'")

        if not self._is_command(text):
            logger.debug("Текст не содержит команду для создания задачи.")
            return None

        try:
            date = self._extract_date(text)
            if date is None:
                logger.debug("Дата не распознана")
                return None

            title = self._extract_title(text)
            if not title:
                logger.debug("Заголовок не распознан")
                return None

            priority = self._extract_priority(text)
            duration = self._extract_duration(text)
            tags = self._extract_tags(text)

            task = Task(
                title=title,
                date=date,
                priority=priority,
                duration_minutes=duration,
                tags=tags,
            )
            logger.info(f"Задача успешно создана: {task}")
            return task

        except Exception as e:
            raise ParsingError(f"Ошибка при парсинге команды: {e}")

    def parse_query_date(self, text: str) -> Optional[datetime]:
        if "сегодня" in text:
            return datetime.now()
        elif "завтра" in text:
            return datetime.now() + timedelta(days=1)
        elif "послезавтра" in text:
            return datetime.now() + timedelta(days=2)

        for name, weekday in self.WEEKDAYS_RU.items():
            if name in text:
                today = datetime.now()
                days_ahead = (weekday - today.weekday() + 7) % 7
                return today + timedelta(days=days_ahead)

        months_pattern = "|".join(self.MONTHS_RU.keys())
        pattern = rf"(\d{{1,2}})[\s\-]?(?:го|ого)?\s+({months_pattern})"
        match = re.search(pattern, text)

        if match:
            day = int(match.group(1))
            month = self.MONTHS_RU[match.group(2)]
            now = datetime.now()
            year = now.year if (month > now.month) else now.year + 1
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        return None

    def _is_command(self, text: str) -> bool:
        return any(word in text for word in self.TRIGGER_WORDS)

    def _extract_date(self, text: str) -> Optional[datetime]:
        now = datetime.now()

        relative_patterns = [
            (r"через\s+(\d+)\s+минут", "minutes"),
            (r"через\s+(\d+)\s+час", "hours"),
            (r"через\s+(\d+)\s+полтора\s+часа", "half_hours"),
            (r"через\s+час", "one_hour"),
        ]

        for pattern, time_type in relative_patterns:
            match = re.search(pattern, text)
            if match:
                if time_type == "minutes":
                    return now + timedelta(minutes=int(match.group(1)))
                elif time_type == "hours":
                    return now + timedelta(hours=int(match.group(1)))
                elif time_type == "half_hours":
                    return now + timedelta(minutes=30)
                elif time_type == "one_hour":
                    return now + timedelta(hours=1)

        if "послезавтра" in text:
            base_date = now + timedelta(days=2)
        elif "завтра" in text:
            base_date = now + timedelta(days=1)
        elif "сегодня" in text:
            base_date = now
        else:
            base_date = self._extract_weekday(text, now)

            if base_date is None:
                base_date = self._extract_calendar_date(text, now)

        if base_date is None:
            return None

        hour, minute = self._extract_time(text)
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _extract_weekday(self, text: str, today: datetime) -> Optional[datetime]:
        for name, weekday in self.WEEKDAYS_RU.items():
            if name in text.split():
                days_ahead = (weekday - today.weekday()) % 7 or 7
                return today + timedelta(days=days_ahead)
        return None

    def _extract_calendar_date(self, text: str, today: datetime) -> Optional[datetime]:
        months_pattern = "|".join(self.MONTHS_RU.keys())
        pattern = rf"(\d{{1,2}})[\s\-]?(?:го|ого)?\s+({months_pattern})"
        match = re.search(pattern, text)

        if match:
            day = int(match.group(1))
            month = self.MONTHS_RU[match.group(2)]

            # Пробуем текущий год
            try:
                candidate = datetime(today.year, month, day)
                # Если дата уже прошла в этом году — берем следующий год
                if candidate.date() < today.date():
                    candidate = datetime(today.year + 1, month, day)
                return candidate
            except ValueError:
                return None

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
        cleaned = text

        stop_words = (
            self.TRIGGER_WORDS
            + self.TASK_KEYWORDS
            + ["мне", "на", "пожалуйста", "будь", "добр"]
        )

        words = cleaned.split()
        words = [word for word in words if word not in stop_words]
        cleaned = " ".join(words)

        for word in self.PRIORITY_KEYWORDS:
            cleaned = cleaned.replace(f"c {word}", "")
            cleaned = cleaned.replace(word, "")

        patterns = [
            rf"\d{{1,2}}[\s\-]?(?:го|ого)?\s+(?:{'|'.join(self.MONTHS_RU)})",
            r"в\s+\d{1,2}[:\-]\d{2}",
            r"в\s+\d{1,2}(?:\s+(?:час|часов|часа))?",
            r"через\s+\d+\s+(?:минут|час)",
            r"через\s+полчаса",
            r"через\s+час",
            r"(?:сегодня|завтра|послезавтра)",
            r"(?:" + "|".join(self.WEEKDAYS_RU) + r")",
            r"на\s+\d+\s+(?:минут|час)",
            r"длительностью\s+\d+\s+(?:минут|час)",
        ]

        for pattern in patterns:
            cleaned = re.sub(pattern, " ", cleaned)

        title = " ".join(cleaned.split())
        title = title.strip(".,!?;:")

        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

        return title if title else None

    def _extract_priority(self, text: str) -> int:
        for word, priority in self.PRIORITY_KEYWORDS.items():
            if word in text.split():
                return priority
        return 0

    def _extract_duration(self, text: str) -> int:
        for pattern, multiplier in self.DURATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1)) * multiplier
        return 60

    def _extract_tags(self, text: str) -> list:
        tags = []

        hashtag_pattern = r"#(\w+)"
        bracket_pattern = r"\[(\w+)\]"

        for match in re.finditer(hashtag_pattern, text):
            tags.append(match.group(1))

        for match in re.finditer(bracket_pattern, text):
            tags.append(match.group(1))

        return list(set(tags))

