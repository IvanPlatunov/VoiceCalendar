"""
Хранилище задач в Google Calendar с поддержкой синхронизации с JSON.
"""

import pickle
import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..models.task import Task
from .base import BaseCalendarStorage
from ..exceptions import StorageError, ConfigurationError

# Цвета Google Calendar для приоритетов
PRIORITY_COLORS = {
    0: "9",  # Синий — низкий
    1: "5",  # Желтый — средний
    2: "11",  # Красный — высокий
}

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarStorage(BaseCalendarStorage):
    """Хранилище задач в Google Calendar."""

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.pickle",
        calendar_id: str = "primary",
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.calendar_id = calendar_id
        self.service = self._authenticate()

    def _authenticate(self):
        """Получает или обновляет токен доступа."""
        creds = self._load_token()

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = self._request_new_token()
            self._save_token(creds)

        return build("calendar", "v3", credentials=creds)

    def _load_token(self) -> Optional[Credentials]:
        """Загружает сохранённый токен."""
        try:
            with open(self.token_path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise StorageError(f"Ошибка загрузки токена: {e}")

    def _save_token(self, creds: Credentials) -> None:
        """Сохраняет токен в файл."""
        try:
            with open(self.token_path, "wb") as f:
                pickle.dump(creds, f)
        except Exception as e:
            raise StorageError(f"Ошибка сохранения токена: {e}")

    def _request_new_token(self) -> Credentials:
        """Запрашивает новый токен через OAuth."""
        if not os.path.exists(self.credentials_path):
            raise ConfigurationError(
                f"Файл credentials.json не найден: {self.credentials_path}\n"
                f"Скачайте файл с https://console.cloud.google.com/"
            )
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            return flow.run_local_server(port=0)  # type: ignore
        except Exception as e:
            raise StorageError(f"Ошибка аутентификации: {e}")

    def _format_datetime_for_api(self, dt: datetime) -> str:
        """
        Форматирует datetime для Google Calendar API.
        Возвращает строку в формате RFC3339 с timezone.
        """
        # Если datetime без timezone, считаем что это Moscow time
        if dt.tzinfo is None:
            moscow_tz = timezone(timedelta(hours=3))
            dt = dt.replace(tzinfo=moscow_tz)

        return dt.isoformat()

    def _parse_datetime(self, dt_string: str) -> datetime:
        """
        Парсит datetime строку из Google Calendar API.
        Обрабатывает timezone-aware строки с 'Z' или смещением.
        """
        if dt_string is None:
            return datetime.now(timezone.utc)

        # Заменяем 'Z' на '+00:00' для совместимости с fromisoformat
        if dt_string.endswith("Z"):
            dt_string = dt_string[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(dt_string)
        except ValueError:
            # Если не получилось распарсить, возвращаем текущее время
            return datetime.now(timezone.utc)

    def _get_task_signature(self, task: Task) -> str:
        """
        Создаёт уникальную подпись задачи для определения дубликатов.
        Формат: "название|YYYY-MM-DD HH:MM"
        """
        date_str = task.date.strftime("%Y-%m-%d %H:%M")
        return f"{task.title.lower().strip()}|{date_str}"

    def _fetch_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        Единый метод для всех GET-запросов к Google Calendar API.
        Устраняет дублирование параметров.
        """
        params = {
            "calendarId": self.calendar_id,
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": limit,
        }
        if time_min:
            params["timeMin"] = self._format_datetime_for_api(time_min)
        if time_max:
            params["timeMax"] = self._format_datetime_for_api(time_max)
        if query:
            params["q"] = query

        try:
            return self.service.events().list(**params).execute().get("items", [])
        except HttpError as e:
            raise StorageError(f"Ошибка Google Calendar API: {e}")

    def _task_to_event(self, task: Task) -> dict:
        """Task → событие Google Calendar."""
        # Рассчитываем время окончания на основе duration_minutes
        start_time = task.date
        end_time = start_time + timedelta(minutes=task.duration_minutes)

        return {
            "summary": task.title,
            "description": task.description or "",
            "start": {
                "dateTime": self._format_datetime_for_api(start_time),
                "timeZone": "Europe/Moscow",
            },
            "end": {
                "dateTime": self._format_datetime_for_api(end_time),
                "timeZone": "Europe/Moscow",
            },
            "colorId": PRIORITY_COLORS.get(task.priority, "9"),
        }

    def _event_to_task(self, event: dict) -> Task:
        """Событие Google Calendar → Task."""
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))

        # Парсим datetime с учётом timezone
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)

        # Расчет продолжительности в минутах
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        if duration_minutes <= 0:
            duration_minutes = 60  # Значение по умолчанию

        # Приоритет по цвету
        color_to_priority = {v: k for k, v in PRIORITY_COLORS.items()}

        # Получаем created_at или используем текущее время
        created_at = datetime.now(timezone.utc)
        if "created" in event:
            created_at = self._parse_datetime(event["created"])

        return Task(
            id=event["id"],
            title=event.get("summary", "Без названия"),
            date=start_dt,
            description=event.get("description"),
            duration_minutes=duration_minutes,
            priority=color_to_priority.get(event.get("colorId", "9"), 0),
            created_at=created_at,
        )

    def add_task(self, task: Task) -> None:
        """Добавляет задачу в календарь."""
        try:
            event = (
                self.service.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=self._task_to_event(task),
                )
                .execute()
            )
            task.id = event["id"]
        except HttpError as e:
            raise StorageError(f"Ошибка создания события: {e}")

    def get_all_tasks(self) -> List[Task]:
        """Возвращает все задачи."""
        events = self._fetch_events()
        return [self._event_to_task(e) for e in events]

    def get_tasks_for_date(self, date: datetime) -> List[Task]:
        """Возвращает задачи на указанную дату."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        events = self._fetch_events(time_min=start, time_max=end)
        return [self._event_to_task(e) for e in events]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Возвращает задачи на ближайшие N дней."""
        now = datetime.now()
        end = now + timedelta(days=days)
        events = self._fetch_events(time_min=now, time_max=end)
        return [self._event_to_task(e) for e in events]

    def find_task_by_id(self, task_id: str) -> Optional[Task]:
        """Ищет задачу по ID."""
        try:
            event = (
                self.service.events()
                .get(
                    calendarId=self.calendar_id,
                    eventId=task_id,
                )
                .execute()
            )
            return self._event_to_task(event)
        except HttpError:
            return None

    def update_task(self, task_id: str, updated_task: Task) -> bool:
        """Обновляет задачу."""
        try:
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=task_id,
                body=self._task_to_event(updated_task),
            ).execute()
            return True
        except HttpError:
            return False

    def delete_task(self, task_id: str) -> bool:
        """Удаляет задачу."""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=task_id,
            ).execute()
            return True
        except HttpError:
            return False

    def search_tasks(self, query: str) -> List[Task]:
        """Ищет задачи по текстовому запросу."""
        events = self._fetch_events(query=query)
        return [self._event_to_task(e) for e in events]

    def get_task_count(self) -> int:
        """Возвращает количество задач."""
        return len(self.get_all_tasks())

    def clear_all(self) -> None:
        """Удаляет все задачи."""
        tasks = self.get_all_tasks()
        for task in tasks:
            self.delete_task(task.id)

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С JSON ==========

    def load_json_tasks(self, json_path: str) -> List[Task]:
        """Загружает задачи из JSON-файла."""
        if not os.path.exists(json_path):
            return []

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)

            if not isinstance(tasks_data, list):
                return []

            return [Task.from_dict(item) for item in tasks_data]
        except (json.JSONDecodeError, Exception):
            return []

    def save_json_tasks(self, json_path: str, tasks: List[Task]) -> None:
        """Сохраняет задачи в JSON-файл."""
        tasks_data = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "title": task.title,
                "date": task.date.isoformat(),
                "description": task.description,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            tasks_data.append(task_dict)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)

    def import_from_json(self, json_path: str) -> int:
        """
        Импортирует задачи из JSON-файла в Google Calendar.

        Args:
            json_path: Путь к JSON-файлу

        Returns:
            Количество импортированных задач
        """
        if not os.path.exists(json_path):
            raise StorageError(f"JSON-файл не найден: {json_path}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)

            if not isinstance(tasks_data, list):
                raise StorageError("Некорректный формат JSON: ожидается массив")

            imported_count = 0
            existing_events = self._fetch_events()
            existing_titles = {e["summary"] for e in existing_events}

            for task_data in tasks_data:
                task = Task.from_dict(task_data)

                # Проверка дубликатов по названию
                if task.title in existing_titles:
                    continue

                # Добавляем задачу
                self.add_task(task)
                imported_count += 1
                existing_titles.add(task.title)

            return imported_count

        except json.JSONDecodeError as e:
            raise StorageError(f"Ошибка чтения JSON: {e}")
        except Exception as e:
            raise StorageError(f"Ошибка импорта: {e}")

    def export_to_json(self, json_path: str) -> int:
        """
        Экспортирует задачи из Google Calendar в JSON-файл.

        Args:
            json_path: Путь для сохранения JSON

        Returns:
            Количество экспортированных задач
        """
        try:
            tasks = self.get_all_tasks()
            self.save_json_tasks(json_path, tasks)
            return len(tasks)
        except Exception as e:
            raise StorageError(f"Ошибка экспорта: {e}")

    # ========== МЕТОД СИНХРОНИЗАЦИИ ==========

    def sync_with_json(self, json_path: str) -> dict:
        """
        Двусторонняя синхронизация между JSON и Google Calendar.

        Логика:
        1. Загружает задачи из обоих источников
        2. Объединяет их (избегая дубликатов по названию + времени)
        3. Сохраняет результат в оба хранилища

        Returns:
            Словарь с информацией о синхронизации:
            - json_tasks: количество задач в JSON
            - google_tasks: количество задач в Google
            - merged_tasks: общее количество после слияния
            - added_to_google: добавлено в Google
            - added_to_json: добавлено в JSON
            - duplicates: количество дубликатов
        """
        result = {
            "json_tasks": 0,
            "google_tasks": 0,
            "merged_tasks": 0,
            "added_to_google": 0,
            "added_to_json": 0,
            "duplicates": 0,
        }

        # 1. Загружаем задачи из обоих источников
        json_tasks = self.load_json_tasks(json_path)
        google_tasks = self.get_all_tasks()

        result["json_tasks"] = len(json_tasks)
        result["google_tasks"] = len(google_tasks)

        # 2. Создаём множества подписей для быстрого поиска дубликатов
        json_signatures = {self._get_task_signature(t) for t in json_tasks}
        google_signatures = {self._get_task_signature(t) for t in google_tasks}

        # 3. Находим уникальные задачи из каждого источника
        unique_json = [
            t
            for t in json_tasks
            if self._get_task_signature(t) not in google_signatures
        ]
        unique_google = [
            t
            for t in google_tasks
            if self._get_task_signature(t) not in json_signatures
        ]

        # Общие задачи (дубликаты)
        common_signatures = json_signatures & google_signatures
        result["duplicates"] = len(common_signatures)

        # 4. Объединяем: общие + уникальные из обоих источников
        merged_tasks = []

        # Добавляем общие задачи из Google (у них уже есть ID)
        for task in google_tasks:
            if self._get_task_signature(task) in common_signatures:
                merged_tasks.append(task)

        # Добавляем уникальные задачи из JSON
        for task in unique_json:
            merged_tasks.append(task)

        # Добавляем уникальные задачи из Google
        for task in unique_google:
            merged_tasks.append(task)

        result["merged_tasks"] = len(merged_tasks)

        # 5. Сохраняем новые задачи из JSON в Google Calendar
        for task in unique_json:
            try:
                self.add_task(task)
                result["added_to_google"] += 1
            except StorageError:
                pass

        # 6. Сохраняем новые задачи из Google в JSON
        for task in unique_google:
            # Для задач из Google создаём новые ID в JSON формате
            task.id = f"gc_{task.id}"
            json_tasks.append(task)
            result["added_to_json"] += 1

        # 7. Сохраняем объединённый список в JSON
        self.save_json_tasks(json_path, merged_tasks)

        return result
