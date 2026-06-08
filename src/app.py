import sys
import time
import os
from datetime import datetime, timedelta
from typing import Optional
from .config import Config
from .storage.json_storage import JsonCalendarStorage
from .storage.google_calendar_storage import GoogleCalendarStorage
from .parser.command_parser import CommandParser
from .speech.recognizer import VoiceRecognizer, RecognizerEvent
from .speech.synthesizer import SpeechSynthesizer


class VoiceCalendarApp:
    # Базовая справка (без блока синхронизации)
    BASE_HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║                   🗓️  VOICE CALENDAR — СПРАВКА                   ║
╠══════════════════════════════════════════════════════════════════╣
║  🔔 АКТИВАЦИЯ                                                    ║
║    • "Привет, календарь" / "Календарь" / "Ассистент"             ║
║                                                                  ║
║  📝 ДОБАВЛЕНИЕ                                                   ║
║    • "Поставь задачу [что] на [когда] в [время]"                 ║
║    • Приоритет: "срочно", "важно"                                ║
║                                                                  ║
║  📋 ПРОСМОТР                                                     ║
║    • "Покажи задачи на сегодня" / "Что у меня на завтра"         ║
║                                                                  ║
║  😴 РЕЖИМЫ                                                       ║
║    • "Стоп", "фон" — фоновый режим                               ║
║    • "Выход" — завершить работу                                  ║
║    • "Помощь" — эта справка                                      ║
║    • "Очисти всё" — удалить все задачи                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

    # Дополнительный блок для режима Google Calendar
    GOOGLE_SYNC_HELP = """
╠══════════════════════════════════════════════════════════════════╣
║  🔄 СИНХРОНИЗАЦИЯ (Google Calendar)                              ║
║    • "Синхронизировать" — объединить JSON и Google Calendar      ║
║    • "Экспорт в json" — сохранить задачи в файл                  ║
║    • "Импорт из json" — загрузить задачи из файла                ║
╚══════════════════════════════════════════════════════════════════╝
"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.config.validate()
        self.parser = CommandParser()
        self.recognizer = VoiceRecognizer(self.config)
        self.synthesizer = SpeechSynthesizer(
            rate=self.config.speech_rate,
            volume=self.config.speech_volume,
            language="ru",
        )

        # Динамический выбор хранилища
        if self.config.storage_type == "google":
            self.storage = GoogleCalendarStorage(
                credentials_path=self.config.google_credentials_path,
                token_path=self.config.google_token_path,
                calendar_id=self.config.google_calendar_id,
            )
            # Автоматическая синхронизация при запуске
            self._auto_sync()
        else:
            self.storage = JsonCalendarStorage(self.config.storage_path)

    def _get_help_text(self) -> str:
        """Возвращает справку с учётом текущего режима работы."""
        if self.config.storage_type == "google":
            return self.BASE_HELP_TEXT + self.GOOGLE_SYNC_HELP
        return self.BASE_HELP_TEXT

    def _get_mode_display(self) -> str:
        """Возвращает строку с отображением текущего режима."""
        if self.config.storage_type == "google":
            return "🌐 Режим: Google Calendar"
        return "💾 Режим: JSON (локальное хранилище)"

    def _auto_sync(self):
        """Автоматическая синхронизация при запуске в режиме Google."""
        json_path = self.config.storage_path

        if not os.path.exists(json_path):
            print("⚠️ JSON-файл не найден, синхронизация пропущена")
            return

        try:
            print("🔄 Выполняется синхронизация с JSON...")
            result = self.storage.sync_with_json(json_path)

            if result["merged_tasks"] > 0:
                print(f"✅ Синхронизация завершена:")
                print(f"   • Задач в JSON: {result['json_tasks']}")
                print(f"   • Задач в Google: {result['google_tasks']}")
                print(f"   • Дубликатов: {result['duplicates']}")
                print(f"   • Итого после слияния: {result['merged_tasks']}")
                print(f"   • Добавлено в Google: {result['added_to_google']}")
                print(f"   • Добавлено в JSON: {result['added_to_json']}")

                self.synthesizer.speak(
                    f"Синхронизация завершена. Всего задач: {result['merged_tasks']}"
                )
            else:
                print("✅ Задач не найдено")

        except Exception as e:
            print(f"️ Ошибка синхронизации: {e}")

    def run(self):
        print("=" * 60)
        print("  ️  VoiceCalendar")
        print(f"  {self._get_mode_display()}")  # ← Отображение режима
        print("Голосовой помощник для управления задачами")
        print("=" * 60)

        self._running = True
        self.synthesizer.speak(
            f"Голосовой помощник готов. "
            f"Работаю в режиме {self.config.storage_type}. "
            f"Чем могу помочь?"
        )

        # Выводим справку с учётом режима
        print(self._get_help_text())

        try:
            while True:
                event, text = self.recognizer.listen_safe()
                if event == RecognizerEvent.WAKE:
                    self.synthesizer.speak("Слушаю!")
                    continue
                elif event == RecognizerEvent.SLEEP:
                    self.synthesizer.speak("Ухожу в фон")
                if text is None:
                    continue
                print(f"\n🗣️ Распознано: {text}")
                self._handle_command(text)
                time.sleep(0.5)
                self.synthesizer.speak("Слушаю!")
        except SystemExit:
            self.synthesizer.speak("До свидания!")
            print("Завершение работы...")
            sys.exit(0)

    def _handle_command(self, text):
        cmd = self.parser.get_command_type(text)

        if cmd == "exit":
            raise SystemExit(0)
        elif cmd == "sleep":
            return
        elif cmd == "show":
            self._cmd_show_tasks(text)
        elif cmd == "help":
            self._cmd_help()
        elif cmd == "clear":
            self._cmd_clear_tasks()
        elif cmd == "sync" and self.config.storage_type == "google":
            self._cmd_sync()
        elif cmd == "export" and self.config.storage_type == "google":
            self._cmd_export_to_json(text)
        elif cmd == "import" and self.config.storage_type == "google":
            self._cmd_import_from_json(text)
        else:
            self._cmd_add_task(text)

    def _cmd_add_task(self, text):
        task = self.parser.parse(text)
        if task:
            self.storage.add_task(task)
            date_str = task.date.strftime("%d %B в %H:%M")
            self.synthesizer.speak(f"Задача [{task.title}] записана на {date_str}")
        else:
            self.synthesizer.speak("Не удалось распознать задачу")

    def _cmd_show_tasks(self, text):
        query_date = self.parser._extract_date(text)
        if query_date:
            tasks = self.storage.get_tasks_for_date(query_date)
            label = f" 📅 Задачи на {query_date.strftime('%d.%m.%Y')}"
        elif "сегодня" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now())
            label = " 📅 Задачи на сегодня"
        elif "завтра" in text:
            tasks = self.storage.get_tasks_for_date(datetime.now() + timedelta(days=1))
            label = " 📅 Задачи на завтра"
        else:
            tasks = self.storage.get_upcoming_tasks(days=7)
            label = " 📅 Задачи на неделю"
        if not tasks:
            self.synthesizer.speak("Задач не найдено")
            return
        print(f"\n{label}")
        for task in tasks:
            print(f" - {task}")
        self.synthesizer.speak(f"Найдено {len(tasks)} задач")

    def _cmd_help(self):
        print("Смотрите список команд на экране")
        # Показываем актуальную справку с режимом
        print(f"\n{self._get_mode_display()}\n")
        print(self._get_help_text())
        self.synthesizer.speak(
            f"Смотрите список команд на экране. "
            f"Текущий режим: {self.config.storage_type}."
        )

    def _cmd_clear_tasks(self) -> None:
        """Очищает все задачи."""
        self.storage.clear_all()
        self.synthesizer.speak("Все задачи удалены")

    def _cmd_sync(self) -> None:
        """Ручная синхронизация JSON и Google Calendar."""
        json_path = self.config.storage_path

        try:
            print("🔄 Выполняется синхронизация...")
            result = self.storage.sync_with_json(json_path)

            message = (
                f"Синхронизация завершена. "
                f"Всего задач: {result['merged_tasks']}. "
                f"Добавлено в Google: {result['added_to_google']}. "
                f"Добавлено в JSON: {result['added_to_json']}"
            )
            self.synthesizer.speak(message)
            print(f"✅ {message}")

        except Exception as e:
            self.synthesizer.speak(f"Ошибка синхронизации: {e}")
            print(f" Ошибка синхронизации: {e}")

    def _cmd_export_to_json(self, text) -> None:
        """Экспортирует задачи в JSON."""
        json_path = self.config.storage_path

        try:
            tasks = self.storage.get_all_tasks()
            self.storage.save_json_tasks(json_path, tasks)
            message = f"Экспортировано {len(tasks)} задач в {json_path}"
            self.synthesizer.speak(message)
            print(f"✅ {message}")
        except Exception as e:
            self.synthesizer.speak(f"Ошибка экспорта: {e}")
            print(f"❌ Ошибка экспорта: {e}")

    def _cmd_import_from_json(self, text) -> None:
        """Импортирует задачи из JSON."""
        json_path = self.config.storage_path

        try:
            imported = self.storage.import_from_json(json_path)
            message = f"Импортировано {imported} задач из {json_path}"
            self.synthesizer.speak(message)
            print(f"✅ {message}")
        except Exception as e:
            self.synthesizer.speak(f"Ошибка импорта: {e}")
            print(f"❌ Ошибка импорта: {e}")


if __name__ == "__main__":
    app = VoiceCalendarApp()
    app.run()
