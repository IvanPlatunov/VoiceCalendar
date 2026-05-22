from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

@dataclass
class Task:
    
    title: str
    date: datetime 
    description: Optional[str] = None
    duration_minutes: int = 60
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


    def __post_init__(self):
        if self.priority not in (0, 1, 2):
            raise ValueError("Ошибка: приоритет должен быть 0 (низкий), 1 (средний) или 2 (высокий).")
        
        if self.duration_minutes <= 0:
            raise ValueError("Ошибка: продолжительность должна быть положительным числом.")

        if not self.title or self.title.strip() == "":
            raise ValueError("Ошибка: заголовок задачи не может быть пустым.")
        

    @property
    def end_time(self) -> datetime:
        return self.date + timedelta(minutes=self.duration_minutes)
    

    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.end_time
    

    @property
    def is_today(self) -> bool:
        self.today = datetime.now().date()
        return self.date.date() == self.today
    

    @property
    def is_tomorrow(self) -> bool:
        self.tommorow = datetime.now().date() + timedelta(days=1)
        return self.date.date() == self.tommorow
    
    @property
    def is_this_week(self) -> bool:
        self.today = datetime.now().date()
        self.start_of_week = self.today - timedelta(days=self.today.weekday())
        end_of_week = self.start_of_week + timedelta(days=6)
        return self.start_of_week <= self.date.date() <= end_of_week
    

    @property
    def priority_Lable(self) -> str:
        self.priority_Lable = {0: "Низкий", 1: "Средний", 2: "Высокий"}
        return self.priority_Lable.get(self.priority, "Неизвестно")
    

    @property
    def priority_icon(self) -> str:
        """Иконка приоритета."""
        icons = {0: "🟢", 1: "🟡", 2: "🔴"}
        return icons.get(self.priority, "⚪")
    

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()


    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()


    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict [str, Any]) -> "Task":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            description=data.get("description"),
            date=datetime.fromisoformat(data["date"]),
            duration_minutes=data.get("duration_minutes", 60),
            priority=data.get("priority", 0),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            tags=data.get("tags", [])
        )
    

    def __str__(self) -> str:
        date_str = self.date.strftime("%d-%m-%Y %H:%M")
        end_str = self.end_time.strftime("%H:%M")
        tags_str = f"[{', '.join(self.tags)}]" if self.tags else ""
        desc_str = f" - {self.description}" if self.description else ""

        return (
            f"{self.priority_icon} [{date_str} - {end_str}]"
            f"{self.title}{tags_str}{desc_str}"
            )
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return self.id == other.id


    def __hash__(self) -> int:
        return hash(self.id)
    
    
    def __lt__(self, other: "Task") -> bool:
        return self.date < other.date