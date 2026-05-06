# source_to_table_service.py
"""Сервис формирования маппинга Источник-Таблица из конфигурационного файла."""

from flask import Response, jsonify

from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from common.error import AppError
from config.db_orm_sqlalchemy.db_session_config import session_scope
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base
from domains.configurator.table_config_parser_service import TableConfigParserService
from domains.information_schema.information_schema_repository import InformationSchemaRepository
from domains.minio.minio_service import MinioService
from domains.project.project_repository import ProjectRepository
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_repository import SourceToTableRepository
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel
from domains.source_to_table.source_to_table_config_repository import SourceToTableConfigRepository

_TC_BUCKET = 'data-pipeline-table-config'


class SourceToTableService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._parser = TableConfigParserService()
        self._minio = MinioService()
        self._project_repository = ProjectRepository()
        self._source_to_table_repository = SourceToTableRepository()
        self._source_to_table_config_repository = SourceToTableConfigRepository()
        self._information_schema_repository = InformationSchemaRepository()

    def generate_mapping_from_config(self, form) -> Response:
        force = form.get('force') == '1'

        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        if not user.db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')

        with session_scope() as session:
            project = self._project_repository.find_by_id(user.project_id, session)
            if not project or not project.table_config_minio_id:
                raise AppError('Конфигурационный файл в системе отсутствует.')
            content = self._minio.download_bytes(_TC_BUCKET, project.table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        if not tables:
            raise AppError('Конфигурационный файл не содержит таблиц.')

        table_names = [t.name for t in tables]

        with working_session_scope_base(int(user.db_id)) as ws:
            table_db_columns: dict[str, list[str]] = {}
            table_serial_cols: dict[str, set[str]] = {}
            for table in tables:
                rows = self._information_schema_repository.get_column_names_with_defaults(
                    user.project_schema, table.name, ws
                )
                table_db_columns[table.name] = [row[0] for row in rows]
                table_serial_cols[table.name] = {
                    row[0].lower() for row in rows
                    if (row[1] or '').lower().startswith('nextval(')
                }

        with session_scope() as session:
            conflicting = self._source_to_table_repository.find_existing_table_names(
                user.project_id, table_names, session
            )

        if conflicting and not force:
            return jsonify(conflicts=conflicting)

        records = []
        for table in tables:
            db_col_names = table_db_columns.get(table.name, [])
            serial_cols = table_serial_cols.get(table.name, set())
            config_by_name = {col.name.lower(): col for col in table.columns}
            config_order = {col.name.lower(): i + 1 for i, col in enumerate(table.columns)}
            for db_col in db_col_names:
                config_col = config_by_name.get(db_col.lower())
                col_lower = db_col.lower()
                func_val = None
                if col_lower in serial_cols:
                    func_val = 'SERIAL'
                elif col_lower == 'package_id':
                    func_val = 'PACKAGE_ID'
                elif col_lower == 'package_timestamp':
                    func_val = 'PACKAGE_TIMESTAMP'
                records.append(SourceToTableModel(
                    project_id=user.project_id,
                    table_name=table.name,
                    source_column=config_col.name if config_col else None,
                    source_column_order=config_order.get(db_col.lower(), 0),
                    source_column_description=config_col.label if config_col else None,
                    table_column=db_col,
                    function=func_val,
                    created_by=user.user_id,
                ))

        with session_scope() as session:
            if conflicting:
                self._source_to_table_repository.delete_by_project_and_tables(
                    user.project_id, table_names, session
                )
                self._source_to_table_config_repository.delete_by_project_and_tables(
                    user.project_id, table_names, session
                )

            if records:
                session.add_all(records)

            existing_cfg_tables = self._source_to_table_config_repository.find_existing_table_names(
                user.project_id, table_names, session
            )
            cfg_records = [
                SourceToTableConfigModel(
                    project_id=user.project_id,
                    table_name=table_name,
                    map_type='MAP_BY_COLUMN_NAME',
                )
                for table_name in table_names
                if table_name not in existing_cfg_tables
            ]
            if cfg_records:
                session.add_all(cfg_records)

        return jsonify(success=True, count=len(records))
