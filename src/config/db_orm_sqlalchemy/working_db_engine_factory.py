# working_db_engine_factory.py
"""Фабрика SQLAlchemy engine для рабочих БД пользователей.

Стратегия инкапсулирована (Strategy pattern), чтобы переключение на кэш-вариант
не затрагивало код вызова. Текущая реализация — без кэша: engine создаётся на
каждый запрос и утилизируется по завершении.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from common.error import AppError
from config.db_orm_sqlalchemy.db_session_config import session_scope
from domains.db_setting.db_setting_model import DbSettingModel


class WorkingDbEngineStrategy(ABC):
    """Стратегия выдачи и освобождения engine рабочей БД."""

    @abstractmethod
    def acquire(self, db_id: int) -> Engine:
        ...

    @abstractmethod
    def release(self, engine: Engine) -> None:
        ...


def _build_working_db_url(setting: DbSettingModel) -> str:
    user = quote_plus(setting.db_user)
    password = quote_plus(setting.password) if setting.password else ''
    auth = f'{user}:{password}@' if password else f'{user}@'
    return f'postgresql+psycopg2://{auth}{setting.host}:{setting.port}/{setting.name}'


def _load_setting(db_id: int) -> DbSettingModel:
    with session_scope() as session:
        setting = session.get(DbSettingModel, db_id)
        if setting is None:
            raise AppError(f'Настройки рабочей БД не найдены: db_id={db_id}.')
        return setting


class NoCacheStrategy(WorkingDbEngineStrategy):
    """Engine на каждый запрос: без пула, с немедленным dispose() при release."""

    def acquire(self, db_id: int) -> Engine:
        setting = _load_setting(db_id)
        url = _build_working_db_url(setting)
        return create_engine(url, poolclass=NullPool, pool_pre_ping=True)

    def release(self, engine: Engine) -> None:
        engine.dispose()


_strategy: WorkingDbEngineStrategy = NoCacheStrategy()


def set_strategy(strategy: WorkingDbEngineStrategy) -> None:
    """Заменить стратегию (например, на кэш-вариант). Использовать при инициализации приложения."""
    global _strategy
    _strategy = strategy


def acquire_working_engine(db_id: int) -> Engine:
    return _strategy.acquire(db_id)


def release_working_engine(engine: Engine) -> None:
    _strategy.release(engine)
