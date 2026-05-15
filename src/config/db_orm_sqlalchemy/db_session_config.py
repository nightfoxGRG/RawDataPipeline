# db_session_config.py
"""Фабрика сессий SQLAlchemy (ленивая инициализация)."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from config.db_orm_sqlalchemy.bd_engine_config import get_engine


_session_factory: sessionmaker | None = None


def _factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def reset_session_factory() -> None:
    """Сбросить фабрику после изменения config (engine также должен быть сброшен)."""
    global _session_factory
    _session_factory = None


def get_session() -> Session:
    """Создать новую сессию. Нужно явно закрыть или использовать session_scope."""
    return _factory()()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Контекстный менеджер: автоматический commit/rollback/close."""
    session = _factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
