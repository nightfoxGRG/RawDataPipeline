#information_schema_repository.py

from sqlalchemy import text as sa_text

from common.db_error_handler import handle_db_errors
from common.singleton_meta import SingletonMeta


@handle_db_errors
class InformationSchemaRepository(metaclass=SingletonMeta):

    def get_base_tables(self, schema: str, session) -> list[str]:
        rows = session.execute(
            sa_text(
                'SELECT table_name FROM information_schema.tables '
                'WHERE table_schema = :s AND table_type = \'BASE TABLE\' '
                'ORDER BY table_name'
            ),
            {'s': schema},
        ).fetchall()
        return [r[0] for r in rows]

    def get_table_columns(self, schema: str, table: str, session) -> list[tuple]:
        return session.execute(
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

    def get_column_names_with_defaults(self, schema: str, table: str, session) -> list[tuple]:
        return session.execute(
            sa_text(
                'SELECT column_name, column_default FROM information_schema.columns '
                'WHERE table_schema = :s AND table_name = :t '
                'ORDER BY ordinal_position'
            ),
            {'s': schema, 't': table},
        ).fetchall()
