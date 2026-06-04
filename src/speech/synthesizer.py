import pyttsx3
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class SpeechSynthesizer:
    
    def __init__(
        self,
        rate: int = 150,
        volume: float = 1.0,
        language: str = "ru",
        voice_gender: Optional[str] = None,
    ):
        self.engine = pyttsx3.init()
        self.rate = rate
        self.volume = volume
        self.language = language
        
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        
        self._set_voice(language, voice_gender)
        
        self._message_queue: List[str] = []
        
        logger.info(
            f"Синтезатор инициализирован: язык={language}, "
            f"скорость={rate}, громкость={volume}"
        )
    
    def _set_voice(self, language: str, gender: Optional[str] = None) -> None:
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
        
        for voice in voices:
            voice_lower = (voice.name + voice.id).lower()
            if any(kw in voice_lower for kw in keywords):
                self.engine.setProperty("voice", voice.id)
                logger.info(f"Выбран голос: {voice.name}")
                return
        
        if voices:
            self.engine.setProperty("voice", voices[0].id)
            logger.info(f"Использован голос по умолчанию: {voices[0].name}")
    
    def list_voices(self) -> List[dict]:
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
        logger.debug(f"Озвучивание: {text}")
        print(f"{text}")
        
        self.engine.say(text)
        
        if blocking:
            self.engine.runAndWait()
    
    def speak_async(self, text: str) -> None:
        self._message_queue.append(text)
        logger.debug(f"Добавлено в очередь: {text}")
    
    def process_queue(self) -> None:
        while self._message_queue:
            text = self._message_queue.pop(0)
            self.speak(text, blocking=True)
    
    def save_to_file(self, text: str, filename: str = "output.mp3") -> None:
        logger.info(f"Сохранение речи в файл: {filename}")
        self.engine.save_to_file(text, filename)
        self.engine.runAndWait()
        print(f"💾 Речь сохранена в: {filename}")
    
    def set_rate(self, rate: int) -> None:
        self.rate = max(50, min(300, rate))
        self.engine.setProperty("rate", self.rate)
        logger.info(f"Скорость изменена: {self.rate}")
    
    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        self.engine.setProperty("volume", self.volume)
        logger.info(f"Громкость изменена: {self.volume}")
    
    def stop(self) -> None:
        self.engine.stop()
        logger.debug("Озвучивание остановлено")
    
    def cleanup(self) -> None:
        self.stop()
        self._message_queue.clear()
        logger.info("Ресурсы синтезатора освобождены")