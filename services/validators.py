import re

from services.models import ConfigParseError, TableConfig


_IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_REFERENCE_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*\([A-Za-z_][A-Za-z0-9_]*\)$')

# subset of PostgreSQL keywords frequently causing naming conflicts
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


def validate_tables(tables: list[TableConfig]) -> list[str]:
    errors: list[str] = []

    table_name_map: dict[str, int] = {}
    for table in tables:
        _validate_identifier('Таблица', table.name, errors)
        if not table.columns:
            errors.append(f'Таблица {table.name} не содержит колонок.')

        table_key = table.name.lower()
        table_name_map[table_key] = table_name_map.get(table_key, 0) + 1

        column_name_map: dict[str, int] = {}
        for column in table.columns:
            _validate_identifier(f'Колонка {table.name}', column.name, errors)
            column_key = column.name.lower()
            column_name_map[column_key] = column_name_map.get(column_key, 0) + 1

            if column.foreign_key:
                _validate_reference(column.foreign_key, table.name, column.name, errors)

        duplicated_columns = sorted(name for name, count in column_name_map.items() if count > 1)
        for duplicated_column in duplicated_columns:
            errors.append(f'В таблице {table.name} найден дубликат колонки: {duplicated_column}.')

    duplicated_tables = sorted(name for name, count in table_name_map.items() if count > 1)
    for duplicated_table in duplicated_tables:
        errors.append(f'Найден дубликат таблицы: {duplicated_table}.')

    return errors


def _validate_identifier(entity: str, value: str, errors: list[str]) -> None:
    if not _IDENTIFIER_PATTERN.match(value):
        errors.append(
            f'{entity} "{value}" содержит недопустимые символы. '
            'Разрешены только латиница, цифры и _, первый символ — буква или _.'
        )
    if value.upper() in _POSTGRES_RESERVED_WORDS:
        errors.append(f'{entity} "{value}" использует зарезервированное слово PostgreSQL.')


def _validate_reference(reference: str, table_name: str, column_name: str, errors: list[str]) -> None:
    if '(' not in reference or not reference.endswith(')'):
        errors.append(
            f'Некорректная ссылка в {table_name}.{column_name}: "{reference}". '
            'Ожидается формат table(column).'
        )
        return

    ref_table, ref_column_part = reference.split('(', 1)
    ref_column = ref_column_part[:-1]
    if not ref_table or not ref_column:
        errors.append(
            f'Некорректная ссылка в {table_name}.{column_name}: "{reference}". '
            'Ожидается формат table(column).'
        )
        return

    _validate_identifier('Таблица (FK)', ref_table, errors)
    _validate_identifier('Колонка (FK)', ref_column, errors)


def _validate_yes_no_cell(value: str | None, field: str, column: str, table: str) -> None:
    if value is None:
        return
    if value.lower() not in {'да', 'нет'}:
        raise ConfigParseError(
            f'Колонка {column} таблицы {table}: поле "{field}" содержит недопустимое значение '
            f'"{value}". Допустимы только "да", "нет" или пустое значение.'
        )


def _validate_reference_cell(value: str | None, column: str, table: str) -> None:
    if value is None:
        return
    if not _REFERENCE_PATTERN.match(value):
        raise ConfigParseError(
            f'Колонка {column} таблицы {table}: некорректный формат ссылки '
            f'"{value}". Ожидается формат table(column).'
        )
