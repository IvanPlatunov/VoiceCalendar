import sys
import argparse
from dotenv import load_dotenv

load_dotenv()
from src.config import Config
from src.app import VoiceCalendarApp
from src.exceptions import VoiceCalendarError, ConfigurationError


def parse_args():
    parser = argparse.ArgumentParser(
        description="VoiceCalendar - голосовой планировщик задач",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=""" 
    Примеры использования:
      python main.py                          # Запуск с настройками по умолчанию
      python main.py --storage json           # JSON-хранилище
      python main.py --storage google         # Google Calendar
      python main.py --language en            # Английский язык
      python main.py --debug                  # Режим отладки
      python main.py --version                # Показать версию
                                     """,
    )
    parser.add_argument(
        "--storage",
        choices=["json", "google"],
        default=None,
        help="Тип хранилища (по умолчанию из переменной окружения VC_STORAGE_TYPE)",
    )

    parser.add_argument(
        "--storage-path", type=str, default=None, help="Путь к файлу JSON-хранилища"
    )

    parser.add_argument(
        "--google-credentials",
        type=str,
        default=None,
        help="Путь к файлу credentials.json для Google Calendar",
    )

    parser.add_argument("--debug", action="store_true", help="Включить режим отладки")

    parser.add_argument("--version", action="version", version="VoiceCalendar v2.0.0")

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Путь к файлу конфигурации (переопределяет остальные параметры)",
    )

    return parser.parse_args()


def create_config(args) -> Config:
    import os

    if args.storage:
        os.environ["VC_STORAGE_TYPE"] = args.storage
    if args.storage_path:
        os.environ["VC_STORAGE_PATH"] = args.storage_path
    if args.google_credentials:
        os.environ["VC_GOOGLE_CREDENTIALS"] = args.google_credentials
    if args.debug:
        os.environ["VC_DEBUG"] = "true"
        os.environ["VC_LOG_LEVEL"] = "DEBUG"
    config = Config.from_env()
    config.validate()
    return config


def main():
    try:
        args = parse_args()
        config = create_config(args)
        if config.debug:
            print("Режим отладки включен")
        app = VoiceCalendarApp(config=config)
        app.run()
    except KeyboardInterrupt:
        print("Работа прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка: {e}")
        if args and args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
