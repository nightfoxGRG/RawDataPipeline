# working_db_repository_decorator.py
import functools
import inspect
from typing import Callable, cast, TypeVar, Any
from sqlalchemy.exc import SQLAlchemyError

from common.db_decorator.working_db_context import WorkingDbContext
from common.error import AppError
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base

F = TypeVar('F', bound=Callable[..., Any])

# проверить как это работает, внедрить везде
def working_db_with_session(func: F) -> F:
    """Декоратор читает db_id из первого аргумента и сохраняет сессию в self._session."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        db_id = args[0] if args else kwargs.get('db_id')
        if db_id is None:
            raise AppError('db_id не передан в метод репозитория.')

        session = WorkingDbContext().get_current_session()

        if session is not None:
            self._session = session
            try:
                return func(self, *args, **kwargs)
            finally:
                if hasattr(self, '_session'):
                    delattr(self, '_session')
        else:
            with working_session_scope_base(int(db_id)) as new_session:
                self._session = new_session
                try:
                    return func(self, *args, **kwargs)
                finally:
                    if hasattr(self, '_session'):
                        delattr(self, '_session')

    return cast(F, wrapper)


def working_db_handle_db_errors(func: F) -> F:
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


def working_db_repository(cls):
    """Декоратор класса: применяет управление сессией и обработку ошибок ко всем методам."""

    for name, obj in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_'):  # Не трогаем приватные методы
            # Сначала обработка ошибок, потом управление сессией
            wrapped = working_db_handle_db_errors(obj)
            wrapped = working_db_with_session(wrapped)
            setattr(cls, name, wrapped)

    return cls