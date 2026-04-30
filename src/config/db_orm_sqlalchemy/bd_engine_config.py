"""Создание SQLAlchemy engine из config.toml / config.local.toml."""
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine
from config.system_db_config import build_url

# Один engine на всё приложение (пул соединений)
engine: Engine = _create_engine(
    build_url(),
    pool_pre_ping=True,   # проверять соединение перед использованием
    echo=False,           # True — выводить SQL в консоль (для отладки)
)

