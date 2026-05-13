from dataclasses import dataclass, field
from datetime import datetime
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
    

