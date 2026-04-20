from services.models import ColumnConfig, TableConfig


_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}


def generate_sql(tables: list[TableConfig]) -> str:
    statements = []
    for table in tables:
        parts_list = [_column_parts(col) for col in table.columns]
        name_width = max(len(p[0]) for p in parts_list)
        type_width = max(len(p[1]) for p in parts_list)

        lines = []
        for name, type_str, constraints, label in parts_list:
            line = f'    {name.ljust(name_width)}  {type_str.ljust(type_width)}'
            if constraints:
                line += f'  {constraints}'
            if label:
                line += f'  -- {label}'
            lines.append(line.rstrip())

        column_lines = ',\n'.join(lines)
        statements.append(f'create table {table.name} (\n{column_lines}\n);')
    return '\n\n'.join(statements)


def format_column(column: ColumnConfig) -> str:
    name, type_str, constraints, label = _column_parts(column)
    result = f'{name} {type_str}'
    if constraints:
        result += f' {constraints}'
    if label:
        result += f' -- {label}'
    return result


def _column_parts(column: ColumnConfig) -> tuple[str, str, str, str]:
    type_str = _format_type(column.db_type, column.size)
    constraints = []

    if not column.nullable:
        constraints.append('not null')
    if column.unique:
        constraints.append('unique')
    if column.default:
        constraints.append(f'default {column.default}')
    if column.primary_key:
        constraints.append('primary key')
    if column.foreign_key:
        constraints.append(f'references {column.foreign_key}')

    return column.name, type_str, ' '.join(constraints), column.label or ''


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
