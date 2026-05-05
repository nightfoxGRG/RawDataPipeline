# table_config_validator.py
import re

from common.singleton_meta import SingletonMeta
from common.error import AppError, ValidationError
from domains.table_config.table_config_model import TableConfig
from domains.sql_generator.postgres_types import (
    is_boolean_type,
    is_known_db_type,
    is_numeric_type,
    is_safe_default_expression,
    looks_like_sql_expression,
)

_IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# table(column) или schema.table(column) — опциональный префикс схемы.
_REFERENCE_PATTERN = re.compile(
    r'^([A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*\([A-Za-z_][A-Za-z0-9_]*\)$'
)
_SIZE_PATTERN = re.compile(r'^\d+(\s*,\s*\d+)?$')

_POSTGRES_RESERVED_WORDS = {
    'ALL', 'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARRAY', 'AS', 'ASC', 'ASYMMETRIC',
    'AUTHORIZATION', 'BINARY', 'BOTH', 'CASE', 'CAST', 'CHECK', 'COLLATE', 'COLUMN',
    'CONSTRAINT', 'CREATE', 'CURRENT_CATALOG', 'CURRENT_DATE', 'CURRENT_ROLE',
    'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURRENT_USER', 'DEFAULT', 'DEFERRABLE',
    'DESC', 'DISTINCT', 'DO', 'ELSE', 'END', 'EXCEPT', 'FALSE', 'FETCH', 'FOR',
    'FOREIGN', 'FROM', 'GRANT', 'GROUP', 'HAVING', 'IN', 'INITIALLY', 'INTERSECT',
    'INTO', 'IS', 'JOIN', 'LEADING', 'LIMIT', 'LOCALTIME', 'LOCALTIMESTAMP',
    'NATURAL', 'NOT', 'NULL', 'OFFSET', 'ON', 'ONLY', 'OR', 'ORDER', 'PLACING',
    'PRIMARY', 'REFERENCES', 'RETURNING', 'SELECT', 'SESSION_USER', 'SOME',
    'SYMMETRIC', 'TABLE', 'THEN', 'TO', 'TRAILING', 'TRUE', 'UNION', 'UNIQUE',
    'USER', 'USING', 'VARIADIC', 'WHEN', 'WHERE', 'WINDOW', 'WITH',
}


class TableConfigValidator(metaclass=SingletonMeta):

    def validate_tables(self, tables: list[TableConfig]) -> None:
        """Проверить таблицы и при наличии проблем выбросить ValidationError со списком ошибок."""
        errors: list[str] = []

        table_name_map: dict[str, int] = {}
        for table in tables:
            self._validate_identifier('Таблица', table.name, errors)
            if not table.columns:
                errors.append(f'Таблица {table.name} не содержит колонок.')

            table_key = table.name.lower()
            table_name_map[table_key] = table_name_map.get(table_key, 0) + 1

            column_name_map: dict[str, int] = {}
            for column in table.columns:
                self._validate_identifier(f'Колонка {table.name}', column.name, errors)
                column_key = column.name.lower()
                column_name_map[column_key] = column_name_map.get(column_key, 0) + 1

                self._validate_db_type(column.db_type, column.name, table.name, errors)
                self._validate_size(column.size, column.name, table.name, errors)

                if column.foreign_key:
                    self._validate_reference(column.foreign_key, table.name, column.name, errors)
                if column.default is not None:
                    self._validate_default_value(column.default, column.db_type, column.name, table.name, errors)

            for name in sorted(n for n, c in column_name_map.items() if c > 1):
                errors.append(f'В таблице {table.name} найден дубликат колонки: {name}.')

        for name in sorted(n for n, c in table_name_map.items() if c > 1):
            errors.append(f'Найден дубликат таблицы: {name}.')

        if errors:
            raise ValidationError(errors=errors)

    def validate_yes_no_cell(self, value: str | None, field: str, column: str, table: str) -> None:
        if value is None:
            return
        if value.lower() not in {'да', 'нет'}:
            raise AppError(
                f'Колонка {column} таблицы {table}: поле "{field}" содержит недопустимое значение '
                f'"{value}". Допустимы только "да", "нет" или пустое значение.'
            )

    def validate_reference_cell(self, value: str | None, column: str, table: str) -> None:
        if value is None:
            return
        if not _REFERENCE_PATTERN.match(value):
            raise AppError(
                f'Колонка {column} таблицы {table}: некорректный формат ссылки '
                f'"{value}". Ожидается формат table(column) или schema.table(column).'
            )

    def _validate_identifier(self, entity: str, value: str, errors: list[str]) -> None:
        if not _IDENTIFIER_PATTERN.match(value):
            errors.append(
                f'{entity} "{value}" содержит недопустимые символы. '
                'Разрешены только латиница, цифры и _, первый символ — буква или _.'
            )
        if value.upper() in _POSTGRES_RESERVED_WORDS:
            errors.append(f'{entity} "{value}" использует зарезервированное слово PostgreSQL.')

    def _validate_reference(self, reference: str, table_name: str, column_name: str, errors: list[str]) -> None:
        format_hint = 'Ожидается формат table(column) или schema.table(column).'

        if '(' not in reference or not reference.endswith(')'):
            errors.append(
                f'Некорректная ссылка в {table_name}.{column_name}: "{reference}". {format_hint}'
            )
            return
        ref_table, ref_column_part = reference.split('(', 1)
        ref_column = ref_column_part[:-1]
        if not ref_table or not ref_column:
            errors.append(
                f'Некорректная ссылка в {table_name}.{column_name}: "{reference}". {format_hint}'
            )
            return

        parts = ref_table.split('.')
        if len(parts) == 1:
            self._validate_identifier('Таблица (FK)', parts[0], errors)
        elif len(parts) == 2:
            self._validate_identifier('Схема (FK)', parts[0], errors)
            self._validate_identifier('Таблица (FK)', parts[1], errors)
        else:
            errors.append(
                f'Некорректная ссылка в {table_name}.{column_name}: "{reference}". {format_hint}'
            )
            return

        self._validate_identifier('Колонка (FK)', ref_column, errors)

    @staticmethod
    def _validate_db_type(db_type: str, column: str, table: str, errors: list[str]) -> None:
        if not db_type or not db_type.strip():
            errors.append(f'Колонка {column} таблицы {table}: тип данных не задан.')
            return
        if not is_known_db_type(db_type):
            errors.append(
                f'Колонка {column} таблицы {table}: тип "{db_type}" не входит в список '
                'допустимых типов PostgreSQL.'
            )

    @staticmethod
    def _validate_size(size: str | None, column: str, table: str, errors: list[str]) -> None:
        if size is None:
            return
        size_str = str(size).strip()
        if not size_str:
            return
        if not _SIZE_PATTERN.match(size_str):
            errors.append(
                f'Колонка {column} таблицы {table}: размер "{size}" должен содержать только '
                'цифры (опционально через запятую, например "100" или "10,2").'
            )

    @staticmethod
    def _validate_default_value(default: str, db_type: str, column: str, table: str, errors: list[str]) -> None:
        if looks_like_sql_expression(default):
            if not is_safe_default_expression(default):
                errors.append(
                    f'Колонка {column} таблицы {table}: значение по умолчанию "{default}" '
                    'не разрешено как SQL-выражение. Допустимы только константы '
                    '(null, true, false, current_timestamp, current_date и т.п.) '
                    'или вызовы функций без аргументов вида name().'
                )
            return
        if is_boolean_type(db_type):
            errors.append(
                f'Колонка {column} таблицы {table}: значение по умолчанию "{default}" '
                f'некорректно для типа {db_type}. '
                'Допустимы только SQL-константы: true, false, null.'
            )
            return
        if is_numeric_type(db_type):
            try:
                float(default)
            except ValueError:
                errors.append(
                    f'Колонка {column} таблицы {table}: значение по умолчанию "{default}" '
                    f'не является допустимым числом для типа {db_type}.'
                )
