"""Синтез речи."""

import pyttsx3


class SpeechSynthesizer:
    def __init__(self, rate: int = 150, volume: float = 1.0, language: str = "ru"):
        self.rate = rate
        self.volume = volume
        self.language = language
        self._voice_id = None
        self._find_voice()

    def _find_voice(self) -> None:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        keyword = "russian" if self.language == "ru" else "english"
        for voice in voices:
            if keyword in voice.name.lower():
                self._voice_id = voice.id
                break
        engine.stop()

    def speak(self, text: str) -> None:
        print(f"🔊 {text}")
        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)
        if self._voice_id:
            engine.setProperty("voice", self._voice_id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
