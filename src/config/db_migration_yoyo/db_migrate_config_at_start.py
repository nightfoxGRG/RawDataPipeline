#db_migrate_config_at_start.py
#""Автоматическое применение миграций БД при старте приложения."""
import traceback
import psycopg2
from yoyo import get_backend, read_migrations
from common.project_paths import ProjectPaths
from config.config_loader import get_config
from config.system_db_config import get_db_url, get_db_system_schema

_MIGRATION_TABLE = '_yoyo_migration'

def run_migrations_on_start() -> None:
    try:
        # Схема system должна существовать до инициализации yoyo
        _ensure_system_schema()

        # Преобразуем Path в строку
        migrations_path = str(ProjectPaths.MIGRATIONS)
        print(f'[migrate] Путь к миграциям: {migrations_path}')

        migrations = read_migrations(migrations_path)
        backend = get_backend(
            build_dsn(),
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

def build_dsn() -> str:
    # search_path указывает yoyo создавать служебные таблицы в схеме system
    return (
        f'{get_db_url()}'
        f'?options=-c%20search_path%3D{get_db_system_schema()}'
    )

def _ensure_system_schema() -> None:
    cfg = get_config()
    db = cfg.get('database', {})
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
            cur.execute(f'create schema if not exists {get_db_system_schema()};')
    finally:
        conn.close()

