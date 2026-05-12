# working_db_transactional.py
import functools

from common.db_decorator.working_db_context import WorkingDbContext
from config.db_orm_sqlalchemy.db_session_config import session_scope

# проверить как это работает
def working_db_transactional(func):
    """Декоратор: все операции внутри одной транзакции."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Если уже внутри транзакции - не создаем новую
        if WorkingDbContext().is_active():
            return func(*args, **kwargs)

        # Создаем новую транзакцию
        with session_scope() as session:
            WorkingDbContext().push_session(session)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                WorkingDbContext().pop_session()

    return wrapper