"""
JSON-хранилище задач.
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
import threading

from src.models.task import Task
from src.storage.base import BaseCalendarStorage
from src.exceptions import StorageError


class JsonCalendarStorage(BaseCalendarStorage):
    """
    Хранилище задач на основе JSON-файла.

    """

    def __init__(self, filepath: str = "calendar_data.json", backup: bool = True):
        """
        Инициализация JSON-хранилища.

        Args:
            filepath: Путь к JSON-файлу.
            backup: Создавать ли резервную копию при сохранении.
        """
        self.filepath = filepath
        self.backup = backup
        self._tasks: List[Task] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Загружает задачи из файла."""
        if not os.path.exists(self.filepath):
            self._tasks = []
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise StorageError("Некорректный формат файла: ожидается массив")

            with self._lock:
                self._tasks = [Task.from_dict(item) for item in data]

        except json.JSONDecodeError as e:
            raise StorageError(
                f"Ошибка чтения JSON из {self.filepath}: {e}. Файл поврежден."
            )
        except KeyError as e:
            raise StorageError(f"Отсутствует обязательное поле в данных: {e}")

    def _save(self) -> None:
        """Сохраняет задачи в файл (атомарная запись)."""
        try:
            with self._lock:
                data = [task.to_dict() for task in self._tasks]

            # Создаем резервную копию
            if self.backup and os.path.exists(self.filepath):
                backup_path = self.filepath + ".bak"
                shutil.copy2(self.filepath, backup_path)

            temp_path = self.filepath + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            os.replace(temp_path, self.filepath)

        except IOError as e:
            raise StorageError(f"Ошибка записи в файл {self.filepath}: {e}")

    def add_task(self, task: Task) -> None:
        """Добавляет задачу."""
        with self._lock:
            self._tasks.append(task)
        self._save()

    def get_all_tasks(self) -> List[Task]:
        """Возвращает все задачи."""
        with self._lock:
            return sorted(self._tasks, key=lambda t: t.date)

    def get_tasks_for_date(self, date: datetime) -> List[Task]:
        """Возвращает задачи на указанную дату."""
        with self._lock:
            return [task for task in self._tasks if task.date.date() == date.date()]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Возвращает задачи на ближайшие N дней."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        with self._lock:
            upcoming = [t for t in self._tasks if now <= t.date <= cutoff]
            return sorted(upcoming, key=lambda t: t.date)

    def update_task(self, task_id: str, updated_task: Task) -> bool:
        """Обновляет задачу."""
        with self._lock:
            for i, task in enumerate(self._tasks):
                if task.id == task_id:
                    updated_task.id = task_id
                    updated_task.created_at = task.created_at
                    self._tasks[i] = updated_task
                    self._save()
                    return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """Удаляет задачу."""
        with self._lock:
            original_count = len(self._tasks)
            self._tasks = [t for t in self._tasks if t.id != task_id]

            if len(self._tasks) < original_count:
                self._save()
                return True
        return False

    def find_task_by_id(self, task_id: str) -> Optional[Task]:
        """Ищет задачу по ID."""
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    return task
        return None

    def get_task_count(self) -> int:
        """Возвращает количество задач."""
        with self._lock:
            return len(self._tasks)

    def search_tasks(self, query: str) -> List[Task]:
        """Ищет задачи по текстовому запросу."""
        query = query.lower()
        with self._lock:
            results = []
            for task in self._tasks:
                if query in task.title.lower() or (
                    task.description and query in task.description.lower()
                ):
                    results.append(task)
            return sorted(results, key=lambda t: t.date)

    def clear_all(self) -> None:
        """Удаляет все задачи."""
        with self._lock:
            self._tasks.clear()
        self._save()

    def export_to_file(self, export_path: str) -> None:
        """
        Экспортирует задачи в другой JSON-файл.

        Args:
            export_path: Путь для экспорта.
        """
        with self._lock:
            data = [task.to_dict() for task in self._tasks]

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_from_file(self, import_path: str) -> int:
        """
        Импортирует задачи из JSON-файла.

        Args:
            import_path: Путь к файлу для импорта.

        Returns:
            Количество импортированных задач.
        """
        if not os.path.exists(import_path):
            raise StorageError(f"Файл не найден: {import_path}")

        with open(import_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported_count = 0
        with self._lock:
            existing_ids = {task.id for task in self._tasks}

            for item in data:
                task = Task.from_dict(item)
                if task.id not in existing_ids:
                    self._tasks.append(task)
                    imported_count += 1

        if imported_count > 0:
            self._save()

        return imported_count
