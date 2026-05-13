# source_to_table_schema_service.py
"""Сервис интерактивного маппинга источника на таблицу."""

from flask import Response, jsonify

from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from common.error import AppError
from domains.working_db.information_schema_repository import InformationSchemaRepository
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_repository import SourceToTableRepository
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel
from domains.source_to_table.source_to_table_config_repository import SourceToTableConfigRepository


class SourceToTableSchemaService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._source_to_table_repository = SourceToTableRepository()
        self._source_to_table_config_repository = SourceToTableConfigRepository()
        self._information_schema_repository = InformationSchemaRepository()

    def list_project_tables(self) -> Response:
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        if not user.db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')
        if not user.project_schema:
            raise AppError('Схема проекта не определена.')

        tables = self._information_schema_repository.get_base_tables(user.db_id, user.project_schema)
        return jsonify(tables=tables)

    def rename_table_config(self, config_id: int, payload: dict) -> Response:
        code = (payload.get('code') or '').strip()
        if not code:
            raise AppError('Код не может быть пустым.')
        description = (payload.get('description') or '').strip() or None
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        found = self._source_to_table_config_repository.update_code_description(
            config_id, user.project_id, code, description,
        )
        if not found:
            raise AppError('Конфигурация не найдена.')
        return jsonify(success=True, code=code, description=description or '')

    def create_table_config(self, table_name: str, payload: dict) -> Response:
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        code = (payload.get('code') or '').strip()
        if not code:
            raise AppError('Код не может быть пустым.')
        description = (payload.get('description') or '').strip() or None
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        config = SourceToTableConfigModel(
            project_id=user.project_id,
            table_name=table_name,
            code=code,
            description=description,
            chunk_size=1000,
            is_auto_generated=False,
            created_by=user.user_id,
        )
        saved = self._source_to_table_config_repository.save(config)
        return jsonify(success=True, id=saved.id, code=saved.code, description=saved.description or '')

    def list_table_configs(self, table_name: str) -> Response:
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        configs = self._source_to_table_config_repository.find_by_project_and_table(user.project_id, table_name)
        return jsonify(configs=[
            {'id': c.id, 'code': c.code, 'description': c.description or ''}
            for c in configs
        ])

    def get_table_mapping(self, table_name: str, config_id: int) -> Response:
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        if not config_id:
            raise AppError('Не указан идентификатор конфигурации.')
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        if not user.db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')
        if not user.project_schema:
            raise AppError('Схема проекта не определена.')

        config = self._source_to_table_config_repository.find_by_id_and_project(config_id, user.project_id)
        if not config:
            raise AppError('Конфигурация маппинга не найдена.')

        rows = self._information_schema_repository.get_table_columns(user.db_id, user.project_schema, table_name)
        if not rows:
            raise AppError(f'Таблица {table_name} не найдена в схеме {user.project_schema}.')

        records = self._source_to_table_repository.find_by_config_id(config_id)
        stored_func = {r.table_column: r.function for r in records}

        table_columns = []
        for col_name, _, comment, col_default in rows:
            if (col_default or '').lower().startswith('nextval('):
                func = 'SERIAL'
                locked = True
            else:
                func = stored_func.get(col_name)
                locked = False
            table_columns.append({
                'name': col_name,
                'function': func,
                'function_locked': locked,
                'description': comment or '',
            })

        mapping = [
            {
                'table_column': r.table_column,
                'function': r.function,
                'source_column': r.source_column,
                'source_column_number': r.source_column_number,
                'source_column_description': r.source_column_description,
            }
            for r in records
        ]

        has_source_name = any(m['source_column'] for m in mapping)
        has_source_number = any(m['source_column_number'] is not None for m in mapping)
        if has_source_number and not has_source_name:
            mapping_type = 'number'
        elif has_source_name and not has_source_number:
            mapping_type = 'name'
        else:
            mapping_type = None

        if mapping_type is None and config.map_type:
            mapping_type = 'name' if config.map_type == 'MAP_BY_COLUMN_NAME' else 'number'

        return jsonify(
            table_columns=table_columns,
            mapping=mapping,
            mapping_type=mapping_type,
            has_mapping=len(mapping) > 0,
            chunk_size=config.chunk_size if config.chunk_size else 1000,
            is_auto_generated=bool(config.is_auto_generated),
        )

    def save_mapping(self, payload: dict) -> Response:
        table_name = (payload.get('table_name') or '').strip()
        if not table_name:
            raise AppError('Не указано имя таблицы.')

        config_id = payload.get('config_id')
        if not config_id:
            raise AppError('Не указан идентификатор конфигурации.')
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            raise AppError('Некорректный идентификатор конфигурации.')

        mapping_type = payload.get('mapping_type')
        if mapping_type not in ('name', 'number'):
            raise AppError('Не указан тип маппинга.')

        chunk_size = payload.get('chunk_size')
        try:
            chunk_size = int(chunk_size) if chunk_size not in ('', None) else 1000
            if chunk_size < 1:
                chunk_size = 1000
        except (TypeError, ValueError):
            chunk_size = 1000

        rows = payload.get('rows') or []
        if not isinstance(rows, list):
            raise AppError('Некорректный формат данных маппинга.')

        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')

        config = self._source_to_table_config_repository.find_by_id_and_project(config_id, user.project_id)
        if not config:
            raise AppError('Конфигурация маппинга не найдена.')

        prepared: list[SourceToTableModel] = []
        for row in rows:
            table_column = (row.get('table_column') or '').strip() or None
            source_column = (row.get('source_column') or '').strip() or None
            source_column_number = row.get('source_column_number')
            if source_column_number in ('', None):
                source_column_number = None
            else:
                ref = table_column or source_column or str(source_column_number)
                try:
                    source_column_number = int(source_column_number)
                except (TypeError, ValueError):
                    raise AppError(f'Некорректный номер колонки для {ref}.')
                if source_column_number < 1:
                    raise AppError(f'Номер колонки для {ref} должен быть положительным числом.')

            if mapping_type == 'name':
                source_column_number = None
            else:
                source_column = None

            has_source = source_column is not None or source_column_number is not None
            if not table_column and not has_source:
                continue

            source_column_description = (row.get('source_column_description') or '').strip() or None
            function = (row.get('function') or '').strip() or None
            source_column_order = row.get('source_column_order')
            try:
                source_column_order = int(source_column_order) if source_column_order not in ('', None) else 0
            except (TypeError, ValueError):
                source_column_order = 0

            prepared.append(
                SourceToTableModel(
                    source_to_table_config_id=config_id,
                    source_column=source_column,
                    source_column_number=source_column_number,
                    source_column_order=source_column_order,
                    source_column_description=source_column_description,
                    table_column=table_column,
                    function=function,
                    created_by=user.user_id,
                )
            )

        map_type = 'MAP_BY_COLUMN_NAME' if mapping_type == 'name' else 'MAP_BY_COLUMN_NUMBER'

        self._source_to_table_repository.delete_by_config_id(config_id)
        if prepared:
            self._source_to_table_repository.save_all(prepared)
        self._source_to_table_config_repository.set_map_type_and_chunk_size(config_id, map_type, chunk_size)

        return jsonify(success=True, count=len(prepared))

    def delete_mapping(self, table_name: str) -> Response:
        table_name = (table_name or '').strip()
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        self._source_to_table_repository.delete_by_project_and_tables(user.project_id, [table_name])
        self._source_to_table_config_repository.delete_by_project_and_tables(user.project_id, [table_name])
        return jsonify(success=True)
