# source_to_table_service.py
"""Сервис формирования маппинга Источник-Таблица из конфигурационного файла."""

from flask import Response, jsonify

from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from common.error import AppError
from domains.configurator.table_config_generator_service import TABLE_CONFIG_BUCKET
from domains.configurator.table_config_parser_service import TableConfigParserService
from domains.generator.sql_generator_service import PACKAGE_ID, PACKAGE_TIMESTAMP, SOURCE
from domains.working_db.information_schema_repository import InformationSchemaRepository
from common.storage.table_config_storage import get_table_config_storage
from domains.project.project_repository import ProjectRepository
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_repository import SourceToTableRepository
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel
from domains.source_to_table.source_to_table_config_repository import SourceToTableConfigRepository


class SourceToTableService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._parser = TableConfigParserService()
        self._storage = get_table_config_storage()
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

        project = self._project_repository.find_by_id(user.project_id)
        if not project or not project.table_config_minio_id:
            raise AppError('Конфигурационный файл в системе отсутствует.')
        content = self._storage.download_bytes(TABLE_CONFIG_BUCKET, project.table_config_minio_id)

        tables = self._parser.parse_tables_config(content, 'config.xlsm')
        if not tables:
            raise AppError('Конфигурационный файл не содержит таблиц.')

        table_names = [t.name for t in tables]

        # (имя колонки, комментарий) — комментарий хранит исходный код колонки,
        # по нему сопоставляем источник, что устойчиво к переименованию id → id_source.
        table_db_columns: dict[str, list[tuple[str, str | None]]] = {}
        table_serial_cols: dict[str, set[str]] = {}
        for table in tables:
            rows = self._information_schema_repository.get_table_columns(
                user.db_id, user.project_schema, table.name,
            )  # (column_name, ordinal_position, comment, column_default)
            table_db_columns[table.name] = [(row[0], row[2]) for row in rows]
            table_serial_cols[table.name] = {
                row[0].lower() for row in rows
                if (row[3] or '').lower().startswith('nextval(')
            }

        conflicting = self._source_to_table_repository.find_existing_table_names(user.project_id, table_names)

        if conflicting and not force:
            return jsonify(conflicts=conflicting)

        if conflicting:
            self._source_to_table_repository.delete_by_project_and_tables(user.project_id, table_names)
            self._source_to_table_config_repository.delete_by_project_and_tables(user.project_id, table_names)

        # Create config records that do not yet exist
        config_code = f'{project.code}_table_config'
        existing_cfg_tables = self._source_to_table_config_repository.find_existing_table_names(
            user.project_id, table_names,
        )
        cfg_records = [
            SourceToTableConfigModel(
                project_id=user.project_id,
                table_name=table_name,
                code=config_code,
                description='маппинг из конфигурационного файла',
                map_type='MAP_BY_COLUMN_NAME',
                chunk_size=1000,
                is_auto_generated=True,
                created_by=user.user_id,
            )
            for table_name in table_names
            if table_name not in existing_cfg_tables
        ]
        if cfg_records:
            self._source_to_table_config_repository.save_all(cfg_records)

        # Build config_id map after configs are persisted
        all_configs = self._source_to_table_config_repository.find_all_by_project_and_tables(
            user.project_id, table_names,
        )
        config_id_map: dict[str, int] = {}
        for cfg in all_configs:
            if cfg.table_name not in config_id_map and cfg.code == config_code:
                config_id_map[cfg.table_name] = cfg.id
        # Fall back to any config for tables not matched by code
        for cfg in all_configs:
            if cfg.table_name not in config_id_map:
                config_id_map[cfg.table_name] = cfg.id

        records: list[SourceToTableModel] = []
        for table in tables:
            config_id = config_id_map.get(table.name)
            if not config_id:
                continue
            db_columns = table_db_columns.get(table.name, [])
            serial_cols = table_serial_cols.get(table.name, set())

            # Источник сопоставляем по комментарию колонки БД: генератор пишет в
            # COMMENT исходный код колонки (label из конфига, либо имя при пустом
            # label). Это устойчиво к переименованию id → id_source и к авто-колонкам
            # (__source/__package_*/auto-id) — их «__»-комментарии не совпадают ни с
            # одним исходным кодом, поэтому они остаются без источника.
            # Ключи: label (приоритет) и имя колонки конфига — на случай пустого label.
            config_lookup: dict[str, tuple] = {}
            for i, col in enumerate(table.columns):
                order = i + 1
                if col.name:
                    config_lookup.setdefault(col.name.strip().lower(), (col, order))
            for i, col in enumerate(table.columns):
                order = i + 1
                if col.label:
                    config_lookup[col.label.strip().lower()] = (col, order)

            for db_col, comment in db_columns:
                col_lower = db_col.lower()

                # bigserial-колонки (nextval) всегда идут как SERIAL без источника.
                if col_lower in serial_cols:
                    records.append(SourceToTableModel(
                        source_to_table_config_id=config_id,
                        source_column=None,
                        source_column_order=0,
                        table_column=db_col,
                        function='SERIAL',
                        created_by=user.user_id,
                    ))
                    continue

                match_key = (comment or '').strip().lower()
                matched = config_lookup.get(match_key) if match_key else None

                func_val = None
                if col_lower == PACKAGE_ID.name:
                    func_val = PACKAGE_ID.function
                elif col_lower == PACKAGE_TIMESTAMP.name:
                    func_val = PACKAGE_TIMESTAMP.function
                elif col_lower == SOURCE.name:
                    func_val = SOURCE.function
                records.append(SourceToTableModel(
                    source_to_table_config_id=config_id,
                    source_column=matched[0].label if matched else None,
                    source_column_order=matched[1] if matched else 0,
                    table_column=db_col,
                    function=func_val,
                    created_by=user.user_id,
                ))

        if records:
            self._source_to_table_repository.save_all(records)

        return jsonify(success=True, count=len(records))
