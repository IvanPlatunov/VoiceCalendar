import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .exceptions import ConfigurationError


@dataclass
class Config:
    storage_type: str = field(
        default_factory=lambda: os.getenv("VC_STORAGE_TYPE", "json")
    )
    storage_path: str = field(
        default_factory=lambda: os.getenv(
            "VC_STORAGE_PATH", str(Path(__file__).parent.parent / "calendar_data.json")
        )
    )
    language: str = field(default_factory=lambda: os.getenv("VC_LANGUAGE", "ru-RU"))
    recognition_timeout: int = field(
        default_factory=lambda: int(os.getenv("VC_RECOGNITION_TIMEOUT", "5"))
    )
    phrase_time_limit: int = field(
        default_factory=lambda: int(os.getenv("VS_PHRASE_TIME_LIMIT", "15"))
    )
    samplerate: int = field(
        default_factory=lambda: int(os.getenv("VC_SAMPLERATE", "16000"))
    )
    speech_rate: int = field(
        default_factory=lambda: int(os.getenv("VC_SPEECH_RATE", "150"))
    )
    speech_volume: float = field(
        default_factory=lambda: float(os.getenv("VC_SPEECH_VOLUME", "0.9"))
    )
    chunk_duration: float = field(
        default_factory=lambda: float(os.getenv("VC_CHUNK_DURATION", "0.3"))
    )
    silence_threshold: int = field(
        default_factory=lambda: int(os.getenv("VC_SILENCE_THRESHOLD", "100"))
    )
    silence_limit: float = field(
        default_factory=lambda: float(os.getenv("VC_SILENCE_LIMIT", "1.5"))
    )

    google_credentials_path: Optional[str] = field(
        default_factory=lambda: os.getenv("VC_GOOGLE_CREDENTIALS", None)
    )
    google_token_path: Optional[str] = field(
        default_factory=lambda: os.getenv("VC_GOOGLE_TOKEN", "token.pickle")
    )
    google_calendar_id: str = field(
        default_factory=lambda: os.getenv("VC_GOOGLE_CALENDAR_ID", "primary")
    )
    default_task_duration: int = field(
        default_factory=lambda: int(os.getenv("VC_DEFAULT_DURATION", "60"))
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("VC_DEBUG", "false").lower() == "true"
    )
    log_level: str = field(default_factory=lambda: os.getenv("VC_LOG_LEVEL", "INFO"))

    @classmethod
    def from_env(cls) -> "Config":
        return cls()

    def validate(self):
        valid_storage_types = ("json", "google")
        if self.storage_type not in valid_storage_types:
            raise ConfigurationError(
                f"Неподдерживаемый тип хранилища - {self.storage_type}"
                f"Допустимые варианты: {valid_storage_types}"
            )
        if self.storage_type == "google" and not self.google_credentials_path:
            raise ConfigurationError(
                "Для использования Google Calendar необходимо указать"
                "VC_GOOGLE_CREDENTIALS"
            )
        if not 0.0 <= self.speech_volume <= 1.0:
            raise ConfigurationError("Громкость речи должна быть от 0 до 1")
        if self.speech_rate < 50 or self.speech_rate > 300:
            raise ConfigurationError("Скорость речи должна быть от 50 до 300")

    def to_dict(self) -> dict:
        """Конвертирует конфигурацию в словарь."""
        return {
            "storage_type": self.storage_type,
            "language": self.language,
            "speech_rate": self.speech_rate,
            "debug": self.debug,
        }
