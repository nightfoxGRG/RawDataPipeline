# bd_engine_config.py
"""Создание SQLAlchemy engine из config.toml / config.local.toml."""
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine
from config.system_db_config import get_db_system_schema, get_db_url

# Один engine на всё приложение (пул соединений)
engine: Engine = _create_engine(
    f"{get_db_url('psycopg2')}?options=-c%20search_path%3D{get_db_system_schema()}",
    pool_pre_ping=True,   # проверять соединение перед использованием
    echo=False,           # True — выводить SQL в консоль (для отладки)
)

