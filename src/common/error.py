# error.py
class AppError(Exception):
    """Базовое прикладное исключение для пользовательских ошибок.

    Хранит список сообщений в `errors`. Для одного сообщения достаточно передать
    его первым позиционным аргументом; для нескольких — через `errors=[...]`.
    """

    def __init__(self, message: str = '', *, errors: list[str] | None = None):
        if errors:
            self.errors: list[str] = list(errors)
            super().__init__('; '.join(self.errors))
        else:
            self.errors = [message] if message else []
            super().__init__(message)


class UploadError(AppError):
    """Ошибка валидации загруженного пользователем файла."""


class ValidationError(AppError):
    """Сервис собрал несколько ошибок валидации и возвращает их пакетом."""
