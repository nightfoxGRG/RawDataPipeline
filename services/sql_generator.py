from services.models import ColumnConfig, TableConfig


_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}


def generate_sql(tables: list[TableConfig]) -> str:
    statements = []
    for table in tables:
        column_lines = ',\n'.join(f'    {format_column(column)}' for column in table.columns)
        statements.append(f'CREATE TABLE IF NOT EXISTS {table.name} (\n{column_lines}\n);')
    return '\n\n'.join(statements)


def format_column(column: ColumnConfig) -> str:
    parts = [column.name, _format_type(column.db_type, column.size)]

    if not column.nullable:
        parts.append('NOT NULL')
    if column.unique:
        parts.append('UNIQUE')
    if column.default:
        parts.append(f'DEFAULT {column.default}')
    if column.primary_key:
        parts.append('PRIMARY KEY')
    if column.foreign_key:
        parts.append(f'REFERENCES {column.foreign_key}')

    return ' '.join(parts)


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
