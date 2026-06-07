import pickle
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.models.task import Task
from src.storage.base import BaseCalendarStorage
from src.exceptions import StorageError, ConfigurationError


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

    def _save_token(self, creds: Credentials) -> None:
        """Сохраняет токен в файл."""
        with open(self.token_path, "wb") as f:
            pickle.dump(creds, f)

    def _request_new_token(self) -> Credentials:
        """Запрашивает новый токен через OAuth."""
        if not __import__("os").path.exists(self.credentials_path):
            raise ConfigurationError(
                f"Файл credentials.json не найден: {self.credentials_path}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
        return flow.run_local_server(port=0)

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
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()
        if query:
            params["q"] = query

        try:
            return self.service.events().list(**params).execute().get("items", [])
        except HttpError as e:
            raise StorageError(f"Ошибка Google Calendar API: {e}")

    def _task_to_event(self, task: Task) -> dict:
        """Task → событие Google Calendar."""
        return {
            "summary": task.title,
            "description": task.description or "",
            "start": {
                "dateTime": task.date.isoformat(),
                "timeZone": "Europe/Moscow",
            },
            "end": {
                "dateTime": task.end_time.isoformat(),
                "timeZone": "Europe/Moscow",
            },
            "colorId": PRIORITY_COLORS.get(task.priority, "9"),
        }

    def _event_to_task(self, event: dict) -> Task:
        """Событие Google Calendar → Task."""
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        # Приоритет по цвету
        color_to_priority = {v: k for k, v in PRIORITY_COLORS.items()}

        return Task(
            id=event["id"],
            title=event.get("summary", "Без названия"),
            date=start_dt,
            description=event.get("description"),
            duration_minutes=int((end_dt - start_dt).total_seconds() / 60),
            priority=color_to_priority.get(event.get("colorId", "9"), 0),
            created_at=datetime.fromisoformat(event["created"]),
        )

    def add_task(self, task: Task) -> None:
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
        return [self._event_to_task(e) for e in self._fetch_events()]

    def get_tasks_for_date(self, date: datetime) -> List[Task]:
        start = date.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        return [
            self._event_to_task(e)
            for e in self._fetch_events(time_min=start, time_max=end)
        ]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        return [
            self._event_to_task(e)
            for e in self._fetch_events(time_min=now, time_max=end)
        ]

    def find_task_by_id(self, task_id: str) -> Optional[Task]:
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
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=task_id,
            ).execute()
            return True
        except HttpError:
            return False

    def search_tasks(self, query: str) -> List[Task]:
        return [self._event_to_task(e) for e in self._fetch_events(query=query)]

    def get_task_count(self) -> int:
        return len(self.get_all_tasks())

    def clear_all(self) -> None:
        for task in self.get_all_tasks():
            self.delete_task(task.id)

