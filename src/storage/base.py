"""
Абстрактный базовый класс для всех хранилищ VoiceCalendar.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.models.task import Task


class BaseCalendarStorage(ABC):
    """
    Абстрактный интерфейс хранилища задач.
    
    """
    
    @abstractmethod
    def add_task(self, task: Task) -> None:
        """
        Добавляет задачу в хранилище.
        
        Args:
            task: Объект задачи для добавления.
        """
        pass
    
    @abstractmethod
    def get_all_tasks(self) -> List[Task]:
        """
        Возвращает все задачи.
        
        Returns:
            Список задач, отсортированных по дате.
        """
        pass
    
    @abstractmethod
    def get_tasks_for_date(self, date: datetime) -> List[Task]:
        """
        Возвращает задачи на указанную дату.
        
        Args:
            date: Дата для фильтрации.
            
        Returns:
            Список задач на эту дату.
        """
        pass
    
    @abstractmethod
    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """
        Возвращает задачи на ближайшие N дней.
        
        Args:
            days: Количество дней вперёд.
            
        Returns:
            Список предстоящих задач.
        """
        pass
    
    @abstractmethod
    def update_task(self, task_id: str, updated_task: Task) -> bool:
        """
        Обновляет существующую задачу.
        
        Args:
            task_id: ID задачи для обновления.
            updated_task: Новые данные задачи.
            
        Returns:
            True если задача обновлена, иначе False.
        """
        pass
    
    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """
        Удаляет задачу.
        
        Args:
            task_id: ID задачи для удаления.
            
        Returns:
            True если задача удалена, иначе False.
        """
        pass
    
    @abstractmethod
    def find_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Ищет задачу по ID.
        
        Args:
            task_id: ID задачи.
            
        Returns:
            Объект Task или None.
        """
        pass
    
    @abstractmethod
    def get_task_count(self) -> int:
        """
        Возвращает общее количество задач.
        
        Returns:
            Количество задач в хранилище.
        """
        pass
    
    @abstractmethod
    def search_tasks(self, query: str) -> List[Task]:
        """
        Ищет задачи по текстовому запросу.
        
        Args:
            query: Поисковый запрос.
            
        Returns:
            Список найденных задач.
        """
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """Удаляет все задачи из хранилища."""
        pass