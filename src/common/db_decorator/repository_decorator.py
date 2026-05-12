# repository_decorator.py
import functools
import inspect
from typing import Callable, cast, TypeVar, Any
from sqlalchemy.exc import SQLAlchemyError
from common.db_decorator.db_context import DbContext
from config.db_orm_sqlalchemy.db_session_config import session_scope
from common.error import AppError

F = TypeVar('F', bound=Callable[..., Any])

# проверить как это работает, внедрить везде
def with_session(func: F) -> F:
    """Декоратор управляет сессией и сохраняет её в self._session."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Получаем текущую сессию из контекста
        session = DbContext().get_current_session()

        if session is not None:
            # Сессия уже существует (внутри транзакции)
            self._session = session
            try:
                return func(self, *args, **kwargs)
            finally:
                # Удаляем временную ссылку
                if hasattr(self, '_session'):
                    delattr(self, '_session')
        else:
            # Создаем новую сессию для автономной операции
            with session_scope() as new_session:
                self._session = new_session
                try:
                    return func(self, *args, **kwargs)
                finally:
                    if hasattr(self, '_session'):
                        delattr(self, '_session')

    return cast(F, wrapper)


def handle_db_errors(func: F) -> F:
    """Декоратор обрабатывает ошибки базы данных."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            # Преобразуем SQLAlchemy ошибку в AppError
            orig = getattr(e, 'orig', None)
            error_msg = str(orig).strip() if orig else str(e).strip()
            raise AppError(error_msg) from e

    return wrapper


def repository(cls):
    """Декоратор класса: применяет управление сессией и обработку ошибок ко всем методам."""

    for name, obj in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_'):  # Не трогаем приватные методы
            # Сначала обработка ошибок, потом управление сессией
            wrapped = handle_db_errors(obj)
            wrapped = with_session(wrapped)
            setattr(cls, name, wrapped)

    return cls