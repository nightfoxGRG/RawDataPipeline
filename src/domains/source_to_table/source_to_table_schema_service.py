# source_to_table_schema_service.py
"""Сервис интерактивного маппинга источника на таблицу."""

from sqlalchemy import text as sa_text
from sqlalchemy.exc import SQLAlchemyError
from flask import Response, g, jsonify

from common.singleton_meta import SingletonMeta
from common.error import AppError
from config.db_orm_sqlalchemy.db_session_config import session_scope
from config.db_orm_sqlalchemy.working_db_session_config import working_session_scope_base
from domains.source_to_table.source_to_table_model import SourceToTableModel
from domains.source_to_table.source_to_table_repository import SourceToTableRepository


class SourceToTableSchemaService(metaclass=SingletonMeta):

    def __init__(self, repository: SourceToTableRepository | None = None) -> None:
        self._repository = repository or SourceToTableRepository()

    @staticmethod
    def _user_context() -> tuple[int, str, int, int]:
        current_user = getattr(g, 'current_user', None)
        project_id = getattr(current_user, 'project_id', None) if current_user else None
        project_schema = getattr(current_user, 'project_schema', None) if current_user else None
        db_id = getattr(current_user, 'db_id', None) if current_user else None
        user_id = getattr(current_user, 'user_id', None) if current_user else None
        if not project_id:
            raise AppError('Проект не определён.')
        if not db_id:
            raise AppError('Рабочая БД не определена для текущего пользователя.')
        if not project_schema:
            raise AppError('Схема проекта не определена.')
        return int(project_id), project_schema, int(db_id), int(user_id) if user_id else None

    def list_project_tables(self) -> Response:
        project_id, project_schema, db_id, _ = self._user_context()
        try:
            with working_session_scope_base(db_id) as ws:
                rows = ws.execute(
                    sa_text(
                        'SELECT table_name FROM information_schema.tables '
                        'WHERE table_schema = :s AND table_type = \'BASE TABLE\' '
                        'ORDER BY table_name'
                    ),
                    {'s': project_schema},
                ).fetchall()
        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e

        return jsonify(tables=[r[0] for r in rows])

    def get_table_mapping(self, table_name: str) -> Response:
        if not table_name:
            raise AppError('Не указано имя таблицы.')
        project_id, project_schema, db_id, _ = self._user_context()

        try:
            with working_session_scope_base(db_id) as ws:
                rows = ws.execute(
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
                    {'s': project_schema, 't': table_name},
                ).fetchall()
        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e

        if not rows:
            raise AppError(f'Таблица {table_name} не найдена в схеме {project_schema}.')

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
            records = self._repository.find_by_project_and_table(project_id, table_name, session)
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

        project_id, _, _, user_id = self._user_context()

        prepared: list[dict] = []
        for row in rows:
            table_column = (row.get('table_column') or '').strip()
            if not table_column:
                continue
            source_column = (row.get('source_column') or '').strip() or None
            source_column_number = row.get('source_column_number')
            if source_column_number in ('', None):
                source_column_number = None
            else:
                try:
                    source_column_number = int(source_column_number)
                except (TypeError, ValueError):
                    raise AppError(f'Некорректный номер колонки для {table_column}.')
            source_column_description = (row.get('source_column_description') or '').strip() or None
            function = (row.get('function') or '').strip() or None
            source_column_order = row.get('source_column_order')
            try:
                source_column_order = int(source_column_order) if source_column_order not in ('', None) else 0
            except (TypeError, ValueError):
                source_column_order = 0

            if mapping_type == 'name':
                source_column_number = None
            else:
                source_column = None

            prepared.append({
                'table_column': table_column,
                'source_column': source_column,
                'source_column_number': source_column_number,
                'source_column_description': source_column_description,
                'source_column_order': source_column_order,
                'function': function,
            })

        try:
            with session_scope() as session:
                session.query(SourceToTableModel).filter(
                    SourceToTableModel.project_id == project_id,
                    SourceToTableModel.table_name == table_name,
                ).delete(synchronize_session=False)
                session.flush()

                if prepared:
                    max_id = session.execute(
                        sa_text('SELECT COALESCE(MAX(id), 0) FROM source_to_table')
                    ).scalar()
                    for i, row in enumerate(prepared):
                        session.add(SourceToTableModel(
                            id=max_id + i + 1,
                            project_id=project_id,
                            table_name=table_name,
                            source_column=row['source_column'],
                            source_column_number=row['source_column_number'],
                            source_column_order=row['source_column_order'],
                            source_column_description=row['source_column_description'],
                            table_column=row['table_column'],
                            function=row['function'],
                            created_by=user_id,
                        ))
        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e

        return jsonify(success=True, count=len(prepared))
