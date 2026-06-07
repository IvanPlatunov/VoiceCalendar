import io
import json
import wave
from enum import Enum
from typing import Optional, List, Tuple

import numpy as np
import sounddevice as sd
import requests

from ..config import Config
from ..exceptions import RecognitionError


class RecognizerEvent(Enum):
    WAKE = "wake"
    SLEEP = "sleep"
    TEXT = "text"


class VoiceRecognizer:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.language = self.config.language
        self.samplerate = self.config.samplerate
        self.phrase_time_limit = self.config.phrase_time_limit
        self.chunk_duration = self.config.chunk_duration
        self.silence_threshold = self.config.silence_threshold
        self.silence_limit = self.config.silence_limit
        self._active = False

    @staticmethod
    def list_microphones() -> List[Tuple[int, str]]:
        return [
            (i, d["name"])
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]

    def listen(self) -> Tuple[RecognizerEvent, Optional[str]]:
        try:
            if not self._active:
                print("Голосовой помощник в режиме ожидания")
                while True:
                    text = self._record_and_recognize()
                    if text:
                        self._active = True
                        print("🟢 Активирован")
                        return RecognizerEvent.WAKE, text

            text = self._record_and_recognize()
            return RecognizerEvent.TEXT, text

        except requests.RequestException as e:
            raise RecognitionError(f"Ошибка сервиса: {e}")

    def listen_safe(self) -> Tuple[RecognizerEvent, Optional[str]]:
        while True:
            try:
                return self.listen()
            except RecognitionError as e:
                msg = str(e)
                if msg == "Тишина":
                    if self._active:
                        continue
                    else:
                        return RecognizerEvent.TEXT, None
                elif msg == "Сон":
                    self._active = False
                    return RecognizerEvent.SLEEP, None
                else:
                    print(f"⚠️  {e}")
                    return RecognizerEvent.TEXT, None

    def _record_and_recognize(self) -> str:
        chunks = []
        silence_time = 0.0
        total_time = 0.0
        started = False

        stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype="int16")
        stream.start()

        while total_time < self.phrase_time_limit:
            chunk, _ = stream.read(int(self.chunk_duration * self.samplerate))
            chunks.append(chunk)
            total_time += self.chunk_duration

            if np.abs(chunk).mean() >= self.silence_threshold:
                started = True
                silence_time = 0.0
            else:
                silence_time += self.chunk_duration

            if started and silence_time >= self.silence_limit:
                break

        stream.stop()
        stream.close()

        if not started:
            raise RecognitionError("Тишина")

        recording = np.concatenate(chunks)
        wav = io.BytesIO()
        with wave.open(wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(recording.tobytes())

        print("⏳ Распознаю...")
        response = requests.post(
            "https://www.google.com/speech-api/v2/recognize",
            params={
                "client": "chromium",
                "lang": self.language,
                "key": "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw",
            },
            data=wav.getvalue(),
            headers={"Content-Type": "audio/l16; rate=16000"},
            timeout=10,
        )

        for line in response.text.splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
                return data["result"][0]["alternative"][0]["transcript"].lower().strip()
            except (KeyError, IndexError, json.JSONDecodeError):
                continue

        raise RecognitionError("Сон" if self._active else "Тишина")
