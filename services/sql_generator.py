from services.models import ColumnConfig, TableConfig


_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}


def generate_sql(tables: list[TableConfig]) -> str:
    statements = []
    for table in tables:
        column_lines = ',\n'.join(f'    {format_column(column)}' for column in table.columns)
        statements.append(f'create table {table.name} (\n{column_lines}\n);')
    return '\n\n'.join(statements)


def format_column(column: ColumnConfig) -> str:
    parts = [column.name, _format_type(column.db_type, column.size)]

    if not column.nullable:
        parts.append('not null')
    if column.unique:
        parts.append('unique')
    if column.default:
        parts.append(f'default {column.default}')
    if column.primary_key:
        parts.append('primary key')
    if column.foreign_key:
        parts.append(f'references {column.foreign_key}')

    result = ' '.join(parts)
    if column.label:
        result += f' -- {column.label}'
    return result


def _format_type(db_type: str, size: str | None) -> str:
    normalized_type = db_type.strip()
    if not size:
        return normalized_type

    lower_type = normalized_type.lower()
    if '(' in normalized_type:
        return normalized_type

    if lower_type in _SIZED_TYPES:
        return f'{normalized_type}({size})'
    return normalized_type
