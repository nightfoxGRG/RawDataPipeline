"""Создание SQLAlchemy engine из config.toml / config.local.toml."""
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine

from config.config_loader import load_config


def _build_url() -> str:
    cfg = load_config()
    db = cfg.get('database', {})
    host = db.get('host', 'localhost')
    port = db.get('port', 5432)
    name = db.get('name', 'postgres')
    user = db.get('user', 'postgres')
    password = db.get('password', '')
    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}'


# Один engine на всё приложение (пул соединений)
engine: Engine = _create_engine(
    _build_url(),
    pool_pre_ping=True,   # проверять соединение перед использованием
    echo=False,           # True — выводить SQL в консоль (для отладки)
)

