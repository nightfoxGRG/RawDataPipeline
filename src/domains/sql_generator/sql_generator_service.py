# sql_generator_service.py
from common.singleton_meta import SingletonMeta
from common.error import AppError
from domains.table_config.table_config_model import ColumnConfig, TableConfig
from domains.sql_generator.postgres_types import is_numeric_type, is_quoted_type, is_sql_expression
from domains.table_config.table_config_parser_service import TableConfigParserService
from domains.table_config.table_config_validator import TableConfigValidator
from domains.minio.minio_service import MinioService
from domains.project.project_repository import ProjectRepository
from config.db_orm_sqlalchemy.db_session_config import session_scope
from flask import g

_TC_BUCKET = 'data-pipeline-table-config'
_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}

_AUTO_PK = ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True, label='Ид')
_PACKAGE_ID = ColumnConfig(name='package_id', db_type='varchar', nullable=False, label='Пакетный ид')
_PACKAGE_TS = ColumnConfig(name='package_timestamp', db_type='timestamptz', nullable=False, label='Пакетный временной штамп')


class SqlGeneratorService(metaclass=SingletonMeta):

    def __init__(
        self,
        parser: TableConfigParserService | None = None,
        validator: TableConfigValidator | None = None,
        minio: MinioService | None = None,
    ) -> None:
        self._parser = parser or TableConfigParserService()
        self._validator = validator or TableConfigValidator()
        self._minio = minio or MinioService()

    def generate_sql_from_system_config(self, form) -> tuple[str, bool, bool]:
        add_pk = form.get('add_pk') == '1'
        add_package_fields = form.get('add_package_fields') == '1'

        current_user = getattr(g, 'current_user', None)
        project_id = getattr(current_user, 'project_id', None) if current_user else None
        project_schema = getattr(current_user, 'project_schema', None) if current_user else None

        if not project_id:
            raise AppError('Проект не определён.')

        with session_scope() as session:
            project = ProjectRepository(session).find_by_id(project_id)
            if not project or not project.table_config_minio_id:
                raise AppError('Конфигурационный файл в системе отсутствует.')
            content = self._minio.download_bytes(_TC_BUCKET, project.table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        self._validator.validate_tables(tables)
        sql_output = self.generate_sql(tables, add_pk=add_pk, add_package_fields=add_package_fields, schema=project_schema)
        return sql_output, add_pk, add_package_fields

    def generate_sql(self, tables: list[TableConfig], add_pk: bool = False, add_package_fields: bool = False, schema: str | None = None) -> str:
        statements = []
        for table in tables:
            columns = list(table.columns)

            if add_pk and not any(c.primary_key for c in columns):
                columns = [_AUTO_PK] + columns

            if add_package_fields:
                existing_names = {c.name.lower() for c in columns}
                need_pkg_id = 'package_id' not in existing_names
                need_pkg_ts = 'package_timestamp' not in existing_names

                if need_pkg_id or need_pkg_ts:
                    ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == 'package_id'), -1)
                    if ref_idx < 0:
                        ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == 'id'), -1)
                    insert_at = ref_idx + 1 if ref_idx >= 0 else 0
                    pkg_cols: list[ColumnConfig] = []
                    if need_pkg_id:
                        pkg_cols.append(_PACKAGE_ID)
                    if need_pkg_ts:
                        pkg_cols.append(_PACKAGE_TS)
                    columns = columns[:insert_at] + pkg_cols + columns[insert_at:]

            parts_list = [self._column_parts(col) for col in columns]
            name_width = max(len(p[0]) for p in parts_list)
            type_width = max(len(p[1]) for p in parts_list)

            base_lines = []
            for name, type_str, constraints, _label in parts_list:
                line = f'    {name.ljust(name_width)}  {type_str.ljust(type_width)}'
                if constraints:
                    line += f'  {constraints}'
                base_lines.append(line.rstrip())

            labelled_widths = [len(base_lines[i]) + 1 for i, (_, _, _, lbl) in enumerate(parts_list) if lbl]
            comment_col = max(labelled_widths, default=0)

            last_idx = len(parts_list) - 1
            lines = []
            for i, (_name, _type_str, _constraints, label) in enumerate(parts_list):
                base = base_lines[i]
                is_last = (i == last_idx)
                if label:
                    prefixed = (base + ',') if not is_last else base
                    lines.append(prefixed.ljust(comment_col) + f'  -- {label}')
                else:
                    lines.append(base if is_last else base + ',')

            qualified_name = f'{schema}.{table.name}' if schema else table.name
            statements.append(f'create table {qualified_name} (\n{"\n".join(lines)}\n);')
        return '\n\n'.join(statements)

    def format_column(self, column: ColumnConfig) -> str:
        name, type_str, constraints, label = self._column_parts(column)
        result = f'{name} {type_str}'
        if constraints:
            result += f' {constraints}'
        if label:
            result += f' -- {label}'
        return result

    def _column_parts(self, column: ColumnConfig) -> tuple[str, str, str, str]:
        type_str = self._format_type(column.db_type, column.size)
        constraints = []
        if not column.nullable:
            constraints.append('not null')
        if column.unique:
            constraints.append('unique')
        if column.default is not None:
            constraints.append(f'default {self._format_default(column.default, column.db_type)}')
        if column.primary_key:
            constraints.append('primary key')
        if column.foreign_key:
            constraints.append(f'references {column.foreign_key}')
        return column.name, type_str, ' '.join(constraints), column.label or ''

    @staticmethod
    def _format_default(value: str, db_type: str) -> str:
        if is_sql_expression(value):
            return value
        if is_numeric_type(db_type):
            return value
        if is_quoted_type(db_type):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        try:
            float(value)
            return value
        except ValueError:
            escaped = value.replace("'", "''")
            return f"'{escaped}'"

    @staticmethod
    def _format_type(db_type: str, size: str | None) -> str:
        normalized_type = db_type.strip()
        if not size:
            return normalized_type
        if '(' in normalized_type:
            return normalized_type
        if normalized_type.lower() in _SIZED_TYPES:
            return f'{normalized_type}({size})'
        return normalized_type
