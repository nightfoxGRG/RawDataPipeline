"""Автоматическое применение миграций БД при старте приложения."""

import traceback
from pathlib import Path

import psycopg2
from yoyo import get_backend, read_migrations

from config.config_loader import load_config

_MIGRATIONS_DIR = str(Path(__file__).parent.parent / 'migrations')
_MIGRATE_SCHEMA = 'system'
_MIGRATION_TABLE = '_yoyo_migration'


def build_dsn(db: dict) -> str:
    host = db.get('host', 'localhost')
    port = db.get('port', 5432)
    name = db.get('name', 'postgres')
    user = db.get('user', 'postgres')
    password = db.get('password', '')
    # search_path указывает yoyo создавать служебные таблицы в схеме system
    return (
        f'postgresql://{user}:{password}@{host}:{port}/{name}'
        f'?options=-c%20search_path%3D{_MIGRATE_SCHEMA}%2Cpublic'
    )


def _ensure_system_schema(db: dict) -> None:
    """Создать схему system если она не существует (нужна до инициализации yoyo)."""
    conn = psycopg2.connect(
        host=db.get('host'),
        port=db.get('port', 5432),
        dbname=db.get('name'),
        user=db.get('user'),
        password=db.get('password', ''),
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'create schema if not exists {_MIGRATE_SCHEMA};')
    finally:
        conn.close()


def run_migrations_on_start() -> None:
    """Применить все ожидающие миграции. Вызывается при старте приложения."""
    cfg = load_config()
    db = cfg.get('database', {})
    if not db.get('host') or not db.get('name'):
        print('[migrate] Параметры подключения к БД не заданы — миграции пропущены.')
        return

    dsn = build_dsn(db)
    try:
        # Схема system должна существовать до инициализации yoyo
        _ensure_system_schema(db)

        migrations = read_migrations(_MIGRATIONS_DIR)
        backend = get_backend(
            dsn,
            migration_table=_MIGRATION_TABLE,
        )
        with backend.lock():
            pending = list(backend.to_apply(migrations))
            if not pending:
                print('[migrate] Новых миграций нет.')
                return
            print(f'[migrate] Применяю {len(pending)} миграций...')
            backend.apply_migrations(backend.to_apply(migrations))
            print('[migrate] Готово.')
    except Exception as exc:
        detail = traceback.format_exc()
        raise RuntimeError(
            f'[migrate] БД недоступна или ошибка миграции: {exc}\n\n{detail}'
        ) from exc




