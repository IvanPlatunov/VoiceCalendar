"""
Фикстуры pytest для тестов VoiceCalendar.
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from src.models.task import Task
from src.storage.json_storage import JsonCalendarStorage


@pytest.fixture
def sample_task():
    """Создает тестовую задачу."""
    return Task(
        title="Тестовая задача",
        date=datetime.now() + timedelta(days=1),
        description="Описание тестовой задачи",
        priority=0
    )


@pytest.fixture
def sample_tasks():
    """Создает набор тестовых задач."""
    now = datetime.now()
    return [
        Task(
            title=f"Задача {i}",
            date=now + timedelta(days=i),
            priority=i % 3
        )
        for i in range(5)
    ]


@pytest.fixture
def temp_storage():
    """Создает временное JSON-хранилище."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmpfile.close()
    
    storage = JsonCalendarStorage(filepath=tmpfile.name, backup=False)
    
    yield storage
    
    # Очистка
    os.unlink(tmpfile.name)


@pytest.fixture
def populated_storage(temp_storage, sample_tasks):
    """Создает хранилище с тестовыми данными."""
    for task in sample_tasks:
        temp_storage.add_task(task)
    return temp_storage