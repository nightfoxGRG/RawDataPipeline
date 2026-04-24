"""Пакет для работы с базой данных."""
from config.sqlalchemy.bd_engine_config import engine
from config.sqlalchemy.db_session_config import get_session

__all__ = ['engine', 'get_session']

