import io
import json
import wave
from typing import Optional, List, Tuple

import sounddevice as sd
import numpy as np
import requests

from ..exceptions import RecognitionError
from ..config import Config


class VoiceRecognizer:
    def __init__(
        self,
        config: Optional[Config] = None,
    ):

        self.config = config or Config.from_env()
        self.language = self.config.language
        self.timeout = self.config.recognition_timeout
        self.phrase_time_limit = self.config.phrase_time_limit
        self.samplerate = self.config.samplerate

    @classmethod
    def list_microphones(cls) -> List[Tuple[int, str]]:
        microphones = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                microphones.append((i, d["name"]))
        return microphones

    def listen(self) -> str:
        try:
            print("Слушаю...")
            recording = sd.rec(
                int(self.phrase_time_limit * self.samplerate),
                samplerate=self.samplerate,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            wav = io.BytesIO()
            with wave.open(wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.samplerate)
                wf.writeframes(recording.tobytes())

            print("Распознаю...")

            url = "https://www.google.com/speech-api/v2/recognize"
            params = {
                "client": "chromium",
                "lang": self.language,
                "key": "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw",
            }
            headers = {"Content-Type": "audio/l16; rate=16000"}
            response = requests.post(
                url, params=params, data=wav.getvalue(), headers=headers
            )
            for line in response.text.splitlines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    return (
                        data["result"][0]["alternative"][0]["transcript"]
                        .lower()
                        .strip()
                    )
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue

            raise RecognitionError("Не удалось распознать речь")

        except requests.RequestException as e:
            raise RecognitionError(f"Ошибка сервиса: {e}")

    def listen_safe(self) -> Optional[str]:
        try:
            return self.listen()
        except RecognitionError as e:
            print(f"Ошибка распознавания: {e}")
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")

        return None
