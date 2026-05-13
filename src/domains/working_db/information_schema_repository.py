#information_schema_repository.py

from sqlalchemy import text as sa_text
from common.db_decorator.working_db_repository_decorator import working_db_repository
from common.singleton_meta import SingletonMeta


@working_db_repository
class InformationSchemaRepository(metaclass=SingletonMeta):

    def schema_exists(self, db_id: int, schema: str) -> bool:
        row = self._session.execute(
            sa_text('SELECT 1 FROM information_schema.schemata WHERE schema_name = :s'),
            {'s': schema},
        ).fetchone()
        return row is not None

    def get_base_tables(self, db_id: int, schema: str) -> list[str]:
        rows = self._session.execute(
            sa_text(
                'SELECT table_name FROM information_schema.tables '
                'WHERE table_schema = :s AND table_type = \'BASE TABLE\' '
                'ORDER BY table_name'
            ),
            {'s': schema},
        ).fetchall()
        return [r[0] for r in rows]

    def get_table_columns(self, db_id: int, schema: str, table: str) -> list[tuple]:
        return self._session.execute(
            sa_text(
                'SELECT c.column_name, c.ordinal_position, pgd.description, c.column_default '
                'FROM information_schema.columns c '
                'LEFT JOIN pg_catalog.pg_statio_all_tables st '
                '  ON st.schemaname = c.table_schema AND st.relname = c.table_name '
                'LEFT JOIN pg_catalog.pg_description pgd '
                '  ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position '
                'WHERE c.table_schema = :s AND c.table_name = :t '
                'ORDER BY c.ordinal_position'
            ),
            {'s': schema, 't': table},
        ).fetchall()

    def get_columns_metadata(self, db_id: int, schema: str, table: str) -> list[tuple]:
        return self._session.execute(
            sa_text(
                'SELECT column_name, data_type, is_nullable, column_default '
                'FROM information_schema.columns '
                'WHERE table_schema = :s AND table_name = :t '
                'ORDER BY ordinal_position'
            ),
            {'s': schema, 't': table},
        ).fetchall()

    def get_column_names_with_defaults(self, db_id: int, schema: str, table: str) -> list[tuple]:
        return self._session.execute(
            sa_text(
                'SELECT column_name, column_default FROM information_schema.columns '
                'WHERE table_schema = :s AND table_name = :t '
                'ORDER BY ordinal_position'
            ),
            {'s': schema, 't': table},
        ).fetchall()
