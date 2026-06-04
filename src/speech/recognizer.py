import speech_recognition as sr
from typing import Optional, List, Tuple
import logging

from exceptions import RecognitionError
from config import Config

logger = logging.getLogger(__name__)


class VoiceRecognizer:
    def __init__(
        self,
        config: Optional[Config],
        dynamic_energy_threshold: bool = True,
        calibration_duration: float = 1.0,
    ):

        self.config = config or Config.from_env()
        self.recognizer = sr.Recognizer()
        self.language = self.config.language
        self.timeout = self.config.recognition_timeout
        self.phrase_time_limit = self.config.phrase_time_limit
        self.energy_threshold = self.config.energy_threshold
        self.dynamic_energy_threshold = dynamic_energy_threshold
        self.calibration_duration = calibration_duration

        # Настройка распознавателя
        if not dynamic_energy_threshold:
            self.recognizer.energy_threshold = self.config.energy_threshold
        else:
            self.recognizer.dynamic_energy_threshold = True

        logger.info(
            f"Распознаватель инициализирован: язык={self.language}, timeout={self.timeout}"
        )

    @classmethod
    def list_microphones(cls) -> List[Tuple[int, str]]:
        microphones = []
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            microphones.append((index, name))
        return microphones

    def calibrate(self, duration: float = 2.0) -> None:
        logger.info(f"Калибровка микрофона ({duration} сек)...")

        with sr.Microphone() as source:
            print(
                f" Калибровка микрофона ({duration} сек)... Говорите что-нибудь или молчите."
            )
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)

        logger.info(
            f"Калибровка завершена. Порог энергии: {self.recognizer.energy_threshold}"
        )
        print(
            f"Калибровка завершена. Порог энергии: {self.recognizer.energy_threshold:.1f}"
        )

    def listen(self) -> str:
        try:
            with sr.Microphone() as source:
                logger.debug("Ожидание речи...")
                print(" Слушаю...")

                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )

            logger.debug("Отправка аудио в Google Speech API...")
            print("Распознаю речь...")

            text = self.recognizer.recognize_google(audio, language=self.language)

            result = text.lower().strip()
            logger.info(f"Распознано: {result}")
            return result

        except sr.WaitTimeoutError as e:
            raise RecognitionError("Время ожидания речи истекло") from e
        except sr.UnknownValueError as e:
            raise RecognitionError("Не удалось распознать речь") from e
        except sr.RequestError as e:
            raise RecognitionError(f"Ошибка сервиса распознавания: {e}") from e
        except Exception as e:
            raise RecognitionError(f"Неизвестная ошибка: {e}") from e

    def listen_safe(self) -> Optional[str]:
        try:
            return self.listen()
        except RecognitionError as e:
            logger.warning(f"Ошибка распознавания: {e}")
            print(f"{e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            print(f"Неожиданная ошибка: {e}")

        return None

    def listen_with_retry(self, max_retries: int = 3) -> Optional[str]:
        for attempt in range(1, max_retries + 1):
            logger.debug(f"Попытка {attempt}/{max_retries}")

            result = self.listen_safe()
            if result:
                return result

            if attempt < max_retries:
                print(f"Попытка {attempt + 1}...")

        logger.warning(f"Не удалось распознать речь за {max_retries} попыток")
        return None

