# working_db_repository.py

from sqlalchemy import text as sa_text

from common.db_decorator.working_db_repository_decorator import working_db_repository
from common.singleton_meta import SingletonMeta


@working_db_repository
class WorkingDbRepository(metaclass=SingletonMeta):

    def execute_ddl(self, db_id: int, schema: str, sql: str) -> None:
        self._session.execute(sa_text(f'SET search_path TO "{schema}"'))
        self._session.connection().exec_driver_sql(sql)

    def execute_insert_batch(self, db_id: int, schema: str, sql: str, params: list[dict]) -> None:
        if not params:
            return
        self._session.execute(sa_text(f'SET search_path TO "{schema}"'))
        self._session.execute(sa_text(sql), params)

    def fetch_chunk(self, db_id: int, schema: str, table: str, offset: int, limit: int) -> list[tuple]:
        sql = sa_text(
            f'SELECT * FROM "{schema}"."{table}" OFFSET :offset LIMIT :limit'
        )
        return self._session.execute(sql, {'offset': offset, 'limit': limit}).fetchall()

    def get_column_names(self, db_id: int, schema: str, table: str) -> list[str]:
        sql = sa_text(
            'SELECT column_name FROM information_schema.columns '
            'WHERE table_schema = :s AND table_name = :t ORDER BY ordinal_position'
        )
        rows = self._session.execute(sql, {'s': schema, 't': table}).fetchall()
        return [r[0] for r in rows]
