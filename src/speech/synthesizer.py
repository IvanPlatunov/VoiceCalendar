"""
Модуль синтеза речи с улучшенными возможностями.
"""

import pyttsx3
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class SpeechSynthesizer:
    """
    Синтезатор речи на основе pyttsx3.
    
    Features:
    - Офлайн-синтез речи
    - Выбор голоса (мужской/женский)
    - Настройка скорости и громкости
    - Сохранение речи в файл
    - Очередь сообщений
    """
    
    def __init__(
        self,
        rate: int = 150,
        volume: float = 1.0,
        language: str = "ru",
        voice_gender: Optional[str] = None,
    ):
        """
        Инициализация синтезатора.
        
        Args:
            rate: Скорость речи (50-300 слов в минуту).
            volume: Громкость (0.0 - 1.0).
            language: Язык ('ru' или 'en').
            voice_gender: Предпочитаемый пол голоса ('male' или 'female').
        """
        self.engine = pyttsx3.init()
        self.rate = rate
        self.volume = volume
        self.language = language
        
        # Настройка параметров
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        
        # Выбор голоса
        self._set_voice(language, voice_gender)
        
        # Очередь сообщений для озвучки
        self._message_queue: List[str] = []
        
        logger.info(
            f"Синтезатор инициализирован: язык={language}, "
            f"скорость={rate}, громкость={volume}"
        )
    
    def _set_voice(self, language: str, gender: Optional[str] = None) -> None:
        """
        Выбирает подходящий голос.
        
        Args:
            language: Язык.
            gender: Предпочитаемый пол голоса.
        """
        voices = self.engine.getProperty("voices")
        
        lang_keywords = {
            "ru": ["russian", "ru", "русский"],
            "en": ["english", "en", "английский"],
        }
        
        gender_keywords = {
            "male": ["male", "мужской", "man"],
            "female": ["female", "женский", "woman", "zira"],
        }
        
        keywords = lang_keywords.get(language, [])
        
        if gender and gender in gender_keywords:
            keywords = gender_keywords[gender] + keywords
        
        # Поиск подходящего голоса
        for voice in voices:
            voice_lower = (voice.name + voice.id).lower()
            if any(kw in voice_lower for kw in keywords):
                self.engine.setProperty("voice", voice.id)
                logger.info(f"Выбран голос: {voice.name}")
                return
        
        # Если не нашли — используем первый доступный
        if voices:
            self.engine.setProperty("voice", voices[0].id)
            logger.info(f"Использован голос по умолчанию: {voices[0].name}")
    
    def list_voices(self) -> List[dict]:
        """
        Возвращает список доступных голосов.
        
        Returns:
            Список словарей с информацией о голосах.
        """
        voices = self.engine.getProperty("voices")
        return [
            {
                "id": voice.id,
                "name": voice.name,
                "languages": voice.languages,
                "gender": voice.gender,
            }
            for voice in voices
        ]
    
    def speak(self, text: str, blocking: bool = True) -> None:
        """
        Озвучивает текст.
        
        Args:
            text: Текст для озвучивания.
            blocking: Блокировать ли выполнение до завершения речи.
        """
        logger.debug(f"Озвучивание: {text}")
        print(f"🔊 {text}")
        
        self.engine.say(text)
        
        if blocking:
            self.engine.runAndWait()
    
    def speak_async(self, text: str) -> None:
        """
        Асинхронное озвучивание (не блокирует выполнение).
        
        Args:
            text: Текст для озвучивания.
        """
        self._message_queue.append(text)
        logger.debug(f"Добавлено в очередь: {text}")
    
    def process_queue(self) -> None:
        """Обрабатывает очередь сообщений."""
        while self._message_queue:
            text = self._message_queue.pop(0)
            self.speak(text, blocking=True)
    
    def save_to_file(self, text: str, filename: str = "output.mp3") -> None:
        """
        Сохраняет озвученный текст в аудиофайл.
        
        Args:
            text: Текст для озвучивания.
            filename: Имя выходного файла.
        """
        logger.info(f"Сохранение речи в файл: {filename}")
        self.engine.save_to_file(text, filename)
        self.engine.runAndWait()
        print(f"💾 Речь сохранена в: {filename}")
    
    def set_rate(self, rate: int) -> None:
        """
        Изменяет скорость речи.
        
        Args:
            rate: Новая скорость (50-300).
        """
        self.rate = max(50, min(300, rate))
        self.engine.setProperty("rate", self.rate)
        logger.info(f"Скорость изменена: {self.rate}")
    
    def set_volume(self, volume: float) -> None:
        """
        Изменяет громкость.
        
        Args:
            volume: Новая громкость (0.0 - 1.0).
        """
        self.volume = max(0.0, min(1.0, volume))
        self.engine.setProperty("volume", self.volume)
        logger.info(f"Громкость изменена: {self.volume}")
    
    def stop(self) -> None:
        """Останавливает текущее озвучивание."""
        self.engine.stop()
        logger.debug("Озвучивание остановлено")
    
    def cleanup(self) -> None:
        """Освобождает ресурсы."""
        self.stop()
        self._message_queue.clear()
        logger.info("Ресурсы синтезатора освобождены")