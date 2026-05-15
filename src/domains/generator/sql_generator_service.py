# sql_generator_service.py
from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from common.error import AppError
from domains.configurator.table_config_generator_service import TABLE_CONFIG_BUCKET
from domains.configurator.table_config_model import ColumnConfig, TableConfig
from domains.generator.postgres_types import (
    is_numeric_type,
    is_quoted_type,
    is_safe_default_expression,
    looks_like_sql_expression,
)
from domains.configurator.table_config_parser_service import TableConfigParserService
from domains.configurator.table_config_validator import TableConfigValidator
from common.storage.table_config_storage import get_table_config_storage
from domains.project.project_repository import ProjectRepository
from domains.working_db.information_schema_repository import InformationSchemaRepository
from domains.working_db.working_db_repository import WorkingDbRepository
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base
from flask import Response, jsonify

from domains.users.model.user_info_model import UserInfoModel

_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}

_AUTO_PK = ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True, label='Ид')
PACKAGE_ID = ColumnConfig(name='__package_id', function = "PACKAGE_ID", db_type='varchar', size='36', nullable=False, label='Пакетный ид')
PACKAGE_TIMESTAMP = ColumnConfig(name='__package_timestamp', function ="PACKAGE_TIMESTAMP", db_type='timestamptz', nullable=False, label='Пакетный временной штамп')
SOURCE = ColumnConfig(name='__source', db_type='varchar', function ="SOURCE", size='200', nullable=False, label='Источник')


class SqlGeneratorService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._parser = TableConfigParserService()
        self._validator = TableConfigValidator()
        self._storage = get_table_config_storage()
        self._project_repository = ProjectRepository()
        self._information_schema_repository = InformationSchemaRepository()
        self._working_db_repository = WorkingDbRepository()

    def _get_table_config_minio_id(self, user: UserInfoModel ) ->  str:

        if not user.project_id:
            raise AppError('Проект не определён.')

        project = self._project_repository.find_by_id(user.project_id)
        if not project or not project.table_config_minio_id:
            raise AppError('Конфигурационный файл в системе отсутствует.')

        return project.table_config_minio_id


    def generate_sql_from_system_config(self, form) -> tuple[str, bool, bool]:
        add_pk = form.get('add_pk') == '1'
        add_package_fields = form.get('add_package_fields') == '1'

        user = ContextService.get_user_info()
        table_config_minio_id = self._get_table_config_minio_id(user)
        content = self._storage.download_bytes(TABLE_CONFIG_BUCKET, table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        self._validator.validate_tables(tables)
        sql_output = self.generate_sql(tables, add_pk=add_pk, add_package_fields=add_package_fields, schema=user.project_schema)
        return sql_output, add_pk, add_package_fields

    def execute_sql_in_working_db(self, form) -> Response:
        """Регенерирует SQL из системного конфига в PostgreSQL-совместимом виде
        и выполняет в рабочей БД пользователя.

        SQL не принимается с клиента — это исключает выполнение произвольного SQL
        через подмену textarea. Контекст подключения (db_id, project_schema)
        берётся из ``g.current_user`` через ``working_session_scope``.
        """
        from sqlalchemy import text as sa_text

        add_pk = form.get('add_pk') == '1'
        add_package_fields = form.get('add_package_fields') == '1'
        create_schema = form.get('create_schema') == '1'

        user = ContextService.get_user_info()
        table_config_minio_id = self._get_table_config_minio_id(user)
        content = self._storage.download_bytes(TABLE_CONFIG_BUCKET, table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        self._validator.validate_tables(tables)
        sql_output = self.generate_sql(
            tables,
            add_pk=add_pk,
            add_package_fields=add_package_fields,
            schema=user.project_schema,
            for_execution=True,
        )

        schema_exists = self._information_schema_repository.schema_exists(user.db_id, user.project_schema)

        if not schema_exists:
            if not create_schema:
                return jsonify(schema_missing=True, schema=user.project_schema)
            with working_session_scope_base(int(user.db_id)) as base_session:
                base_session.execute(sa_text(f'CREATE SCHEMA "{user.project_schema}"'))

        self._working_db_repository.execute_ddl(user.db_id, user.project_schema, sql_output)

        return jsonify(success=True)

    def generate_sql(
        self,
        tables: list[TableConfig],
        add_pk: bool = False,
        add_package_fields: bool = False,
        schema: str | None = None,
        for_execution: bool = False,
    ) -> str:
        statements = []
        for table in tables:
            columns = list(table.columns)

            if add_pk and not any(c.primary_key for c in columns):
                columns = [_AUTO_PK] + columns

            if add_package_fields:
                existing_names = {c.name.lower() for c in columns}
                need_pkg_id = PACKAGE_ID.name not in existing_names
                need_pkg_ts = PACKAGE_TIMESTAMP.name not in existing_names
                need_source = SOURCE.name not in existing_names

                if need_pkg_id or need_pkg_ts or need_source:
                    ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == PACKAGE_ID.name), -1)
                    if ref_idx < 0:
                        ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == 'id'), -1)
                    insert_at = ref_idx + 1 if ref_idx >= 0 else 0
                    pkg_cols: list[ColumnConfig] = []
                    if need_source:
                        pkg_cols.append(SOURCE)
                    if need_pkg_id:
                        pkg_cols.append(PACKAGE_ID)
                    if need_pkg_ts:
                        pkg_cols.append(PACKAGE_TIMESTAMP)
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

            last_idx = len(parts_list) - 1
            qualified_name = f'"{schema}"."{table.name}"' if schema else f'"{table.name}"'

            if for_execution:
                # PostgreSQL-совместимый: COMMENT ON COLUMN отдельными statement'ами.
                lines = [
                    base_lines[i] if i == last_idx else base_lines[i] + ','
                    for i in range(len(parts_list))
                ]
                block = (
                    f'drop table if exists {qualified_name};\n'
                    f'create table {qualified_name} (\n{chr(10).join(lines)}\n);'
                )
                comment_lines = [
                    f'comment on column {qualified_name}."{name}" is \'{label.replace(chr(39), chr(39)*2)}\';'
                    for name, _, _, label in parts_list
                    if label
                ]
                if comment_lines:
                    block += '\n' + '\n'.join(comment_lines)
            else:
                # Отображение: inline `COMMENT 'label'` (читаемый формат).
                labelled_widths = [len(base_lines[i]) + 1 for i, (_, _, _, lbl) in enumerate(parts_list) if lbl]
                comment_col = max(labelled_widths, default=0)
                lines = []
                for i, (_name, _type_str, _constraints, label) in enumerate(parts_list):
                    base = base_lines[i]
                    is_last = (i == last_idx)
                    if label:
                        escaped = label.replace("'", "''")
                        suffix = ',' if not is_last else ''
                        lines.append(base.ljust(comment_col) + f"  COMMENT '{escaped}'{suffix}")
                    else:
                        lines.append(base if is_last else base + ',')
                block = (
                    f'drop table if exists {qualified_name};\n'
                    f'create table {qualified_name} (\n{chr(10).join(lines)}\n);'
                )

            statements.append(block)
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
        if looks_like_sql_expression(value):
            if not is_safe_default_expression(value):
                raise AppError(f'Небезопасное значение по умолчанию: "{value}".')
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
