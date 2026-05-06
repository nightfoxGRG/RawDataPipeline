# source_to_table_service.py
"""Сервис формирования маппинга Источник-Таблица из конфигурационного файла."""

from sqlalchemy import text as sa_text
from sqlalchemy.exc import SQLAlchemyError
from flask import Response, g, jsonify

from common.singleton_meta import SingletonMeta
from common.error import AppError
from config.db_orm_sqlalchemy.db_session_config import session_scope
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base
from domains.configurator.table_config_parser_service import TableConfigParserService
from domains.minio.minio_service import MinioService
from domains.project.project_repository import ProjectRepository
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel

_TC_BUCKET = 'data-pipeline-table-config'


class SourceToTableService(metaclass=SingletonMeta):

    def __init__(
        self,
        parser: TableConfigParserService | None = None,
        minio: MinioService | None = None,
    ) -> None:
        self._parser = parser or TableConfigParserService()
        self._minio = minio or MinioService()

    def generate_mapping_from_config(self, form) -> Response:
        force = form.get('force') == '1'

        current_user = getattr(g, 'current_user', None)
        project_id = getattr(current_user, 'project_id', None) if current_user else None
        project_schema = getattr(current_user, 'project_schema', None) if current_user else None
        db_id = getattr(current_user, 'db_id', None) if current_user else None
        user_id = getattr(current_user, 'user_id', None) if current_user else None

        if not project_id:
            raise AppError('Проект не определён.')
        if not db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')

        with session_scope() as session:
            project = ProjectRepository().find_by_id(project_id, session)
            if not project or not project.table_config_minio_id:
                raise AppError('Конфигурационный файл в системе отсутствует.')
            content = self._minio.download_bytes(_TC_BUCKET, project.table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        if not tables:
            raise AppError('Конфигурационный файл не содержит таблиц.')

        table_names = [t.name for t in tables]

        try:
            with working_session_scope_base(int(db_id)) as ws:
                table_db_columns: dict[str, list[str]] = {}
                table_serial_cols: dict[str, set[str]] = {}
                for table in tables:
                    rows = ws.execute(
                        sa_text(
                            'SELECT column_name, column_default FROM information_schema.columns '
                            'WHERE table_schema = :s AND table_name = :t '
                            'ORDER BY ordinal_position'
                        ),
                        {'s': project_schema, 't': table.name},
                    ).fetchall()
                    table_db_columns[table.name] = [row[0] for row in rows]
                    table_serial_cols[table.name] = {
                        row[0].lower() for row in rows
                        if (row[1] or '').lower().startswith('nextval(')
                    }
        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e

        with session_scope() as session:
            conflicting = [
                row[0] for row in (
                    session.query(SourceToTableModel.table_name)
                    .filter(
                        SourceToTableModel.project_id == project_id,
                        SourceToTableModel.table_name.in_(table_names),
                    )
                    .distinct()
                    .all()
                )
            ]

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
                    project_id=project_id,
                    table_name=table.name,
                    source_column=config_col.name if config_col else None,
                    source_column_order=config_order.get(db_col.lower(), 0),
                    source_column_description=config_col.label if config_col else None,
                    table_column=db_col,
                    function=func_val,
                    created_by=user_id,
                ))

        try:
            with session_scope() as session:
                if conflicting:
                    session.query(SourceToTableModel).filter(
                        SourceToTableModel.project_id == project_id,
                        SourceToTableModel.table_name.in_(table_names),
                    ).delete(synchronize_session=False)
                    session.query(SourceToTableConfigModel).filter(
                        SourceToTableConfigModel.project_id == project_id,
                        SourceToTableConfigModel.table_name.in_(table_names),
                    ).delete(synchronize_session=False)

                if records:
                    max_id = session.execute(
                        sa_text('SELECT COALESCE(MAX(id), 0) FROM source_to_table')
                    ).scalar()
                    for i, rec in enumerate(records):
                        rec.id = max_id + i + 1
                    session.add_all(records)

                existing_cfg_tables = {
                    row[0] for row in (
                        session.query(SourceToTableConfigModel.table_name)
                        .filter(
                            SourceToTableConfigModel.project_id == project_id,
                            SourceToTableConfigModel.table_name.in_(table_names),
                        )
                        .all()
                    )
                }
                cfg_records = []
                for table_name in table_names:
                    if table_name not in existing_cfg_tables:
                        cfg_records.append(SourceToTableConfigModel(
                            project_id=project_id,
                            table_name=table_name,
                            map_type='MAP_BY_COLUMN_NAME',
                        ))
                if cfg_records:
                    max_cfg_id = session.execute(
                        sa_text('SELECT COALESCE(MAX(id), 0) FROM source_to_table_config')
                    ).scalar()
                    for i, rec in enumerate(cfg_records):
                        rec.id = max_cfg_id + i + 1
                    session.add_all(cfg_records)

        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e

        return jsonify(success=True, count=len(records))
