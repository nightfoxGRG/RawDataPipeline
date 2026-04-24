"""Фабрика сессий SQLAlchemy."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from config.sqlalchemy.bd_engine_config import engine

_SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    """Создать новую сессию. Нужно явно закрыть или использовать session_scope."""
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Контекстный менеджер: автоматический commit/rollback/close.

    Использование:
        with session_scope() as session:
            repo = UserRepository(session)
            repo.add(user)
    """
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

