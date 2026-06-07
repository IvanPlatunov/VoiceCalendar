import io
import json
import wave
from typing import Optional, List, Tuple

import sounddevice as sd
import numpy as np
import requests

from ..exceptions import RecognitionError
from ..config import Config
from ..parser.command_parser import CommandParser


class VoiceRecognizer:
    def __init__(
        self,
        config: Optional[Config] = None,
    ):

        self.config = config or Config.from_env()
        self.language = self.config.language
        self.phrase_time_limit = self.config.phrase_time_limit
        self.samplerate = self.config.samplerate
        self.chunk_duration = self.config.chunk_duration
        self.silence_threshold = self.config.silence_threshold
        self.silence_limit = self.config.silence_limit
        self._active = False

    @classmethod
    def list_microphones(cls) -> List[Tuple[int, str]]:
        microphones = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                microphones.append((i, d["name"]))
        return microphones

    def listen(self) -> str:
        try:
            if not self._active:
                print("Голосовой помощник в режиме ожидания")
                while True:
                    text = self._record_and_recognize()
                    if text and any(w in text for w in CommandParser.WAKE_WORDS):
                        print("🟢 Активирован")
                        self._active = True
                        break

            while True:
                text = self._record_and_recognize()
                if any(w in text.split() for w in CommandParser.SLEEP_WORDS):
                    self._active = False
                    raise RecognitionError("Сон")
                return text
        except requests.RequestException as e:
            raise RecognitionError(f"Ошибка сервиса: {e}")

    def _record_and_recognize(self):
        chunks = []
        silence_time = 0.0
        total_time = 0.0
        started = False

        stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="int16",
        )
        stream.start()

        while total_time < self.phrase_time_limit:
            chunk, _ = stream.read(int(self.chunk_duration * self.samplerate))
            chunks.append(chunk)
            total_time += self.chunk_duration

            volume = np.abs(chunk).mean()

            if volume >= self.silence_threshold:
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

        print("Распознаю...")

        url = "https://www.google.com/speech-api/v2/recognize"
        params = {
            "client": "chromium",
            "lang": self.language,
            "key": "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw",
        }
        headers = {"Content-Type": "audio/l16; rate=16000"}
        response = requests.post(
            url, params=params, data=wav.getvalue(), headers=headers, timeout=10
        )
        for line in response.text.splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
                return data["result"][0]["alternative"][0]["transcript"].lower().strip()
            except (KeyError, IndexError, json.JSONDecodeError):
                continue

        raise RecognitionError("Не удалось распознать речь")

    def listen_safe(self) -> Optional[str]:
        while True:
            try:
                return self.listen()
            except RecognitionError as e:
                if str(e) == "Тишина":
                    continue
                elif str(e) == "Сон":
                    continue
                else:
                    print(f"Ошибка распознавания: {e}")
                    return None
