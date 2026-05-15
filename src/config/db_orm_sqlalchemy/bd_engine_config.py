# bd_engine_config.py
"""Создание SQLAlchemy engine из config.toml / config.local.toml.

Engine создаётся лениво — это позволяет приложению стартовать без валидного
конфига (для onboarding-страницы в local-режиме).
"""
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine

from config.system_db_config import get_db_system_schema, get_db_url


_engine: Engine | None = None


def get_engine() -> Engine:
    """Вернуть SQLAlchemy engine (создать при первом вызове)."""
    global _engine
    if _engine is None:
        _engine = _create_engine(
            f"{get_db_url('psycopg2')}?options=-c%20search_path%3D{get_db_system_schema()}",
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def reset_engine() -> None:
    """Сбросить engine (после изменения config). Закрывает пул соединений."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
