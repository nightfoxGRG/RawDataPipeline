# working_db_session_config.py
"""Контекст сессии для работы с рабочей БД пользователя.

Параметры подключения и схема берутся из ``g.current_user`` (db_id, project_schema)
если не переданы явно. Engine получается через стратегию, см.
working_db_engine_factory.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Generator

from flask import g
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from common.error import AppError
from config.db_orm_sqlalchemy.working_db_engine_factory import (
    acquire_working_engine,
    release_working_engine,
)

# search_path подставляется в SQL литералом — валидируем формат идентификатора Postgres.
_SCHEMA_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')


@contextmanager
def working_session_scope_base(db_id: int) -> Generator[Session, None, None]:
    """Сессия к рабочей БД без установки search_path (для проверки/создания схемы)."""
    engine = acquire_working_engine(db_id)
    try:
        session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    finally:
        release_working_engine(engine)


@contextmanager
def working_session_scope(
    db_id: int | None = None,
    schema: str | None = None,
) -> Generator[Session, None, None]:
    db_id, schema = _resolve_context(db_id, schema)

    engine = acquire_working_engine(db_id)
    try:
        session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
        try:
            session.execute(text(f'SET search_path TO "{schema}"'))
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    finally:
        release_working_engine(engine)


def _resolve_context(db_id: int | None, schema: str | None) -> tuple[int, str]:
    if db_id is None or schema is None:
        current_user = getattr(g, 'current_user', None)
        if current_user is None:
            raise AppError('Контекст пользователя не установлен.')
        if db_id is None:
            db_id = getattr(current_user, 'db_id', None)
        if schema is None:
            schema = getattr(current_user, 'project_schema', None)

    if not db_id:
        raise AppError('Рабочая БД не определена для текущего пользователя.')
    if not schema:
        raise AppError('Схема проекта не определена для текущего пользователя.')
    if not _SCHEMA_RE.match(schema):
        raise AppError(f'Недопустимое имя схемы: {schema!r}.')

    return int(db_id), schema
