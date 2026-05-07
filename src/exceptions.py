class VoiceCalendarError(Exception):
    def __init__(self, message="Ошибка в VoiceCalendar"):
        self.message = message
        super().__init__(self.message)


class RecognitionError(VoiceCalendarError):
    def __init__(self, message="Не удалось распознать речь"):
        super().__init__(message)


class ParsingError(VoiceCalendarError):
    def __init__(self, message="Не удалось определить команду"):
        super().__init__(message)


class StorageError(VoiceCalendarError):
    def __init__(self, message="Ошибка при работе с хранилищем"):
        super().__init__(message)


class ConfigurationError(VoiceCalendarError):
    def __init__(self, message="Ошибка в конфигурации приложения"):
        super().__init__(message)


class AuthenticationError(VoiceCalendarError):
    def __init__(self, message="Ошибка аутентификации"):
        super().__init__(message)
