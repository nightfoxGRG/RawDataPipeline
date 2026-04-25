from services.models import ColumnConfig, TableConfig
from api.sql_generator.pg_types import is_numeric_type, is_quoted_type, is_sql_expression
from src.util.file_util import UploadError, read_uploaded_file
from api.table_config.table_config_parser_service import parse_tables_config
from services.validators import validate_tables
from services.models import ConfigParseError


_SIZED_TYPES = {'varchar', 'character varying', 'char', 'character', 'numeric', 'decimal'}

_AUTO_PK = ColumnConfig(
    name='id',
    db_type='bigserial',
    nullable=False,
    primary_key=True,
    label='Ид',
)

_PACKAGE_ID = ColumnConfig(name='package_id', db_type='varchar', nullable=False, label='Пакетный ид')
_PACKAGE_TS = ColumnConfig(name='package_timestamp', db_type='timestamptz', nullable=False, label='Пакетный временной штамп')


def generate_sql_from_config(files, form) -> tuple[str, list[str], bool, bool]:
    """Обработать запрос на генерацию SQL.

    Возвращает (sql_output, errors, add_pk, add_package_fields).
    """
    sql_output = ''
    errors = []
    add_pk = form.get('add_pk') == '1'
    add_package_fields = form.get('add_package_fields') == '1'

    try:
        content, filename = read_uploaded_file(files.get('config_file'))
        tables = parse_tables_config(content, filename)
        errors = validate_tables(tables)
        if not errors:
            sql_output = generate_sql(tables, add_pk=add_pk, add_package_fields=add_package_fields)
    except (UploadError, ConfigParseError) as exc:
        errors.append(str(exc))

    return sql_output, errors, add_pk, add_package_fields


def generate_sql(tables: list[TableConfig], add_pk: bool = False, add_package_fields: bool = False) -> str:
    statements = []
    for table in tables:
        columns = list(table.columns)

        # Добавить id если нет первичного ключа
        if add_pk and not any(c.primary_key for c in columns):
            columns = [_AUTO_PK] + columns

        # Добавить package_id, package_timestamp если отсутствуют
        if add_package_fields:
            existing_names = {c.name.lower() for c in columns}
            need_pkg_id = 'package_id' not in existing_names
            need_pkg_ts = 'package_timestamp' not in existing_names

            if need_pkg_id or need_pkg_ts:
                # Точка вставки: после package_id (если есть), иначе после id (если есть), иначе в начало
                ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == 'package_id'), -1)
                if ref_idx < 0:
                    ref_idx = next((i for i, c in enumerate(columns) if c.name.lower() == 'id'), -1)
                insert_at = ref_idx + 1 if ref_idx >= 0 else 0

                # package_id вставляем первым, package_timestamp — за ним
                pkg_cols: list[ColumnConfig] = []
                if need_pkg_id:
                    pkg_cols.append(_PACKAGE_ID)
                if need_pkg_ts:
                    pkg_cols.append(_PACKAGE_TS)

                columns = columns[:insert_at] + pkg_cols + columns[insert_at:]
        parts_list = [_column_parts(col) for col in columns]
        name_width = max(len(p[0]) for p in parts_list)
        type_width = max(len(p[1]) for p in parts_list)

        # Build base lines (without comma or comment) so we can measure their widths
        base_lines = []
        for name, type_str, constraints, _label in parts_list:
            line = f'    {name.ljust(name_width)}  {type_str.ljust(type_width)}'
            if constraints:
                line += f'  {constraints}'
            base_lines.append(line.rstrip())

        # Align comments: pad every base line + comma to the max width of labelled lines.
        # Add 1 to account for the comma that precedes the comment on non-last lines.
        labelled_widths = [len(base_lines[i]) + 1 for i, (_, _, _, lbl) in enumerate(parts_list) if lbl]
        comment_col = max(labelled_widths, default=0)

        last_idx = len(parts_list) - 1
        lines = []
        for i, (_name, _type_str, _constraints, label) in enumerate(parts_list):
            base = base_lines[i]
            is_last = (i == last_idx)
            if label:
                # Comma goes before the comment; last line has no trailing comma
                prefixed = (base + ',') if not is_last else base
                lines.append(prefixed.ljust(comment_col) + f'  -- {label}')
            else:
                lines.append(base if is_last else base + ',')

        column_lines = '\n'.join(lines)
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
    if column.default is not None:
        constraints.append(f'default {_format_default(column.default, column.db_type)}')
    if column.primary_key:
        constraints.append('primary key')
    if column.foreign_key:
        constraints.append(f'references {column.foreign_key}')

    return column.name, type_str, ' '.join(constraints), column.label or ''


def _format_default(value: str, db_type: str) -> str:
    """Return a properly-formatted SQL DEFAULT expression for *value* and *db_type*.

    - SQL keyword constants (NULL, TRUE, FALSE, CURRENT_TIMESTAMP, …) and
      function calls (e.g. now()) are returned verbatim.
    - Numeric types: returned verbatim (validation ensures it is a valid number).
    - Boolean types: returned verbatim (TRUE/FALSE are already handled as SQL
      constants; invalid values pass through and are reported by the validator).
    - String and date/time types: wrapped in single quotes with internal
      single-quotes escaped as ''.
    - Unknown types: quoted if not purely numeric, otherwise verbatim.
    """
    if is_sql_expression(value):
        return value

    if is_numeric_type(db_type):
        return value

    if is_quoted_type(db_type):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    # Unknown / unsupported type: quote unless the value is clearly numeric.
    try:
        float(value)
        return value
    except ValueError:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"


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
