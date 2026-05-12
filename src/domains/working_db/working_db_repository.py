# working_db_repository.py

from sqlalchemy import text as sa_text

from common.db_decorator.working_db_repository_decorator import working_db_repository
from common.singleton_meta import SingletonMeta


@working_db_repository
class WorkingDbRepository(metaclass=SingletonMeta):

    def execute_ddl(self, db_id: int, schema: str, sql: str) -> None:
        self._session.execute(sa_text(f'SET search_path TO "{schema}"'))
        self._session.connection().exec_driver_sql(sql)
