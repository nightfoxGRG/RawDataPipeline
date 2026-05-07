# src/common/db_decorator/transactional.py
import functools

from common.db_decorator.db_context import DbContext
from config.db_orm_sqlalchemy.db_session_config import session_scope


def transactional(func):
    """Декоратор: все операции внутри одной транзакции."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Если уже внутри транзакции - не создаем новую
        if DbContext().is_active():
            return func(*args, **kwargs)

        # Создаем новую транзакцию
        with session_scope() as session:
            DbContext().push_session(session)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                DbContext().pop_session()

    return wrapper