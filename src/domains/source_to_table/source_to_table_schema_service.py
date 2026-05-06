# source_to_table_schema_service.py
"""Сервис интерактивного маппинга источника на таблицу."""

from flask import Response, jsonify

from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from common.error import AppError
from config.db_orm_sqlalchemy.db_session_config import session_scope
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base
from domains.information_schema.information_schema_repository import InformationSchemaRepository
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_repository import SourceToTableRepository
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
        with working_session_scope_base(user.db_id) as ws:
            tables = self._information_schema_repository.get_base_tables(user.project_schema, ws)
        return jsonify(tables=tables)

    def get_table_mapping(self, table_name: str) -> Response:
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        if not user.db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')
        if not user.project_schema:
            raise AppError('Схема проекта не определена.')

        with working_session_scope_base(user.db_id) as ws:
            rows = self._information_schema_repository.get_table_columns(user.project_schema, table_name, ws)

        if not rows:
            raise AppError(f'Таблица {table_name} не найдена в схеме {user.project_schema}.')

        table_columns = []
        for col_name, _ord, comment, col_default in rows:
            col_lower = (col_name or '').lower()
            func = None
            locked = False
            if (col_default or '').lower().startswith('nextval('):
                func = 'SERIAL'
                locked = True
            elif col_lower == 'package_id':
                func = 'PACKAGE_ID'
            elif col_lower == 'package_timestamp':
                func = 'PACKAGE_TIMESTAMP'
            table_columns.append({
                'name': col_name,
                'function': func,
                'function_locked': locked,
                'description': comment or '',
            })

        with session_scope() as session:
            records = self._source_to_table_repository.find_by_project_and_table(user.project_id, table_name, session)
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

        return jsonify(
            table_columns=table_columns,
            mapping=mapping,
            mapping_type=mapping_type,
            has_mapping=len(mapping) > 0,
        )

    def save_mapping(self, payload: dict) -> Response:
        table_name = (payload.get('table_name') or '').strip()
        if not table_name:
            raise AppError('Не указано имя таблицы.')

        mapping_type = payload.get('mapping_type')
        if mapping_type not in ('name', 'number'):
            raise AppError('Не указан тип маппинга.')

        rows = payload.get('rows') or []
        if not isinstance(rows, list):
            raise AppError('Некорректный формат данных маппинга.')

        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')

        prepared: list[dict] = []
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

            # пропускаем строки без каких-либо данных
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

            prepared.append({
                'table_column': table_column,
                'source_column': source_column,
                'source_column_number': source_column_number,
                'source_column_description': source_column_description,
                'source_column_order': source_column_order,
                'function': function,
            })

        map_type = 'MAP_BY_COLUMN_NAME' if mapping_type == 'name' else 'MAP_BY_COLUMN_NUMBER'

        with session_scope() as session:
            self._source_to_table_repository.delete_by_project_and_table(
                user.project_id, table_name, session
            )

            if prepared:
                for row in prepared:
                    session.add(SourceToTableModel(
                        project_id=user.project_id,
                        table_name=table_name,
                        source_column=row['source_column'],
                        source_column_number=row['source_column_number'],
                        source_column_order=row['source_column_order'],
                        source_column_description=row['source_column_description'],
                        table_column=row['table_column'],
                        function=row['function'],
                        created_by=user.user_id,
                    ))

            self._source_to_table_config_repository.upsert_map_type(
                user.project_id, table_name, map_type, session
            )

        return jsonify(success=True, count=len(prepared))

    def delete_mapping(self, table_name: str) -> Response:
        table_name = (table_name or '').strip()
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        user = ContextService.get_user_info()
        if not user.project_id:
            raise AppError('Проект не определён.')
        with session_scope() as session:
            self._source_to_table_repository.delete_by_project_and_table(
                user.project_id, table_name, session
            )
            self._source_to_table_config_repository.delete_by_project_and_table(
                user.project_id, table_name, session
            )
        return jsonify(success=True)
