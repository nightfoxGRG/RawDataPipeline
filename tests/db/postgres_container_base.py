# postgres_container_base.py
"""Базовый класс для тестов репозиториев с реальной БД PostgreSQL в Docker."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg2

os.environ.setdefault('TESTCONTAINERS_RYUK_DISABLED', 'true')
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer
from yoyo import get_backend, read_migrations

_MIGRATIONS_PATH = Path(__file__).parent.parent.parent / 'resources' / 'migrations'
_POSTGRES_IMAGE = 'postgres:latest'
_SYSTEM_SCHEMA = 'system'
_MIGRATION_TABLE = '_yoyo_migration'


class PostgresContainerBase:
    """Поднимает контейнер PostgreSQL один раз на класс, применяет миграции.

    Использование:
        class TestUsersRepository(PostgresContainerBase):
            def test_something(self):
                with self.session_scope() as session:
                    repo = UsersRepository()
                    result = repo.find_user_info_by_subject_id('LOCAL_USER', session)
                    assert result is not None
    """

    _container: PostgresContainer
    _engine: Engine
    _session_factory: sessionmaker

    @classmethod
    def setup_class(cls) -> None:
        cls._container = PostgresContainer(_POSTGRES_IMAGE)
        cls._container.start()
        url = cls._container.get_connection_url()
        cls._engine = create_engine(
            url,
            echo=False,
            connect_args={'options': f'-c search_path={_SYSTEM_SCHEMA}'},
        )
        cls._session_factory = sessionmaker(bind=cls._engine, expire_on_commit=False)
        cls._create_system_schema()
        cls._apply_migrations()

    @classmethod
    def teardown_class(cls) -> None:
        cls._engine.dispose()
        cls._container.stop()

    def setup_method(self) -> None:
        """Открыть сессию перед каждым тестом."""
        self._session = self._session_factory()

    def teardown_method(self) -> None:
        """Откатить все изменения после теста — данные не сохраняются."""
        self._session.rollback()
        self._session.close()

    @property
    def session(self) -> Session:
        """Сессия в рамках текущего теста (откатывается после теста)."""
        return self._session

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Контекстный менеджер для сессии с автоматическим commit/rollback."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def _create_system_schema(cls) -> None:
        params = cls._container
        conn = psycopg2.connect(
            host=params.get_container_host_ip(),
            port=params.get_exposed_port(5432),
            dbname=params.dbname,
            user=params.username,
            password=params.password,
        )
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS {_SYSTEM_SCHEMA};')
        finally:
            conn.close()

    @classmethod
    def _apply_migrations(cls) -> None:
        # yoyo требует postgresql://, SQLAlchemy использует postgresql+psycopg2://
        dsn = cls._container.get_connection_url().replace('postgresql+psycopg2://', 'postgresql://')
        dsn_with_schema = f'{dsn}?options=-c%20search_path%3D{_SYSTEM_SCHEMA}'

        migrations = read_migrations(str(_MIGRATIONS_PATH))
        backend = get_backend(dsn_with_schema, migration_table=_MIGRATION_TABLE)
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))
