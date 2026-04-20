import configparser
import json
from io import BytesIO
from pathlib import Path

import toml
import yaml
from openpyxl import load_workbook

from services.models import ColumnConfig, TableConfig


class ConfigParseError(ValueError):
    """Raised when the config file cannot be parsed."""


TABLE_NAME_LABELS = {'наименование таблицы', 'table_name', 'table name'}
COLUMN_CODE_LABELS = {'код колонки в бд', 'column_code', 'column code'}
TYPE_LABELS = {'тип', 'type'}
SIZE_LABELS = {'размерность', 'size', 'length'}
REQUIRED_LABELS = {'обязательность', 'required', 'nullable'}
UNIQUE_LABELS = {'уникальность', 'unique'}
KEY_LABELS = {'ключ', 'key'}
REFERENCE_LABELS = {'ссылка на таблицу', 'reference', 'references'}
DEFAULT_LABELS = {'default', 'значение по умолчанию'}


def parse_tables_config(content: bytes, filename: str) -> list[TableConfig]:
    extension = Path(filename).suffix.lower()
    if extension in {'.xlsx', '.xlsm'}:
        tables = _parse_excel(content)
    elif extension in {'.yaml', '.yml'}:
        data = yaml.safe_load(content.decode('utf-8'))
        tables = _parse_structured_tables(data)
    elif extension == '.json':
        data = json.loads(content.decode('utf-8'))
        tables = _parse_structured_tables(data)
    elif extension == '.toml':
        data = toml.loads(content.decode('utf-8'))
        tables = _parse_structured_tables(data)
    elif extension == '.ini':
        data = _parse_ini(content)
        tables = _parse_structured_tables(data)
    else:
        raise ConfigParseError('Неподдерживаемый формат файла.')

    if not tables:
        raise ConfigParseError('Секция tables_config не найдена или не содержит таблиц.')
    return tables


def _parse_ini(content: bytes) -> dict:
    parser = configparser.ConfigParser()
    parser.read_string(content.decode('utf-8'))
    result: dict[str, dict] = {}
    for section in parser.sections():
        result[section] = dict(parser.items(section))
    return result


def _parse_structured_tables(data: dict | None) -> list[TableConfig]:
    if not isinstance(data, dict):
        raise ConfigParseError('Некорректная структура конфигурации.')

    tables_config = data.get('tables_config')
    if tables_config is None:
        raise ConfigParseError('Секция tables_config отсутствует.')

    tables: list[TableConfig] = []
    if isinstance(tables_config, dict):
        iterable = [
            {'name': table_name, 'columns': columns}
            for table_name, columns in tables_config.items()
        ]
    elif isinstance(tables_config, list):
        iterable = tables_config
    else:
        raise ConfigParseError('Секция tables_config должна быть словарем или списком.')

    for table_item in iterable:
        if not isinstance(table_item, dict):
            raise ConfigParseError('Каждая таблица в tables_config должна быть объектом.')
        table_name = _normalize_text(table_item.get('name'))
        if not table_name:
            raise ConfigParseError('У таблицы отсутствует имя.')
        columns_raw = table_item.get('columns', [])
        if isinstance(columns_raw, dict):
            columns_raw = [{'name': name, **details} for name, details in columns_raw.items()]
        if not isinstance(columns_raw, list):
            raise ConfigParseError(f'Колонки таблицы {table_name} должны быть списком или словарем.')

        columns: list[ColumnConfig] = []
        for column_item in columns_raw:
            if not isinstance(column_item, dict):
                raise ConfigParseError(f'Некорректное описание колонки в таблице {table_name}.')
            column_name = _normalize_text(column_item.get('name'))
            db_type = _normalize_text(column_item.get('type'))
            if not column_name or not db_type:
                raise ConfigParseError(f'Колонка в таблице {table_name} должна содержать name и type.')

            columns.append(
                ColumnConfig(
                    name=column_name,
                    db_type=db_type,
                    size=_normalize_text(column_item.get('size')),
                    nullable=_to_bool(column_item.get('nullable', True), default=True),
                    unique=_to_bool(column_item.get('unique', False), default=False),
                    primary_key=_to_bool(column_item.get('primary_key', False), default=False),
                    foreign_key=_normalize_text(column_item.get('foreign_key')),
                    default=_normalize_text(column_item.get('default')),
                )
            )

        tables.append(TableConfig(name=table_name, columns=columns))

    return tables


def _parse_excel(content: bytes) -> list[TableConfig]:
    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = _find_tables_sheet(workbook)
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]

    tables: list[TableConfig] = []
    row_index = 0
    while row_index < len(rows):
        current_label = _label(rows[row_index][0] if rows[row_index] else None)
        if current_label in TABLE_NAME_LABELS:
            table, row_index = _parse_excel_table_block(rows, row_index)
            if table is not None:
                tables.append(table)
            continue
        row_index += 1

    return tables


def _find_tables_sheet(workbook):
    for sheet in workbook.worksheets:
        if sheet.title.strip().lower() == 'tables_config':
            return sheet
    if len(workbook.worksheets) == 1:
        return workbook.worksheets[0]
    raise ConfigParseError('Лист tables_config не найден.')


def _parse_excel_table_block(rows: list[list], start_index: int) -> tuple[TableConfig | None, int]:
    header_row = rows[start_index]
    table_name = _first_non_empty(header_row[1:])
    if not table_name:
        return None, start_index + 1

    end_index = start_index + 1
    row_map: dict[str, list] = {}
    while end_index < len(rows):
        row = rows[end_index]
        first_value = row[0] if row else None
        label = _label(first_value)
        if label in TABLE_NAME_LABELS:
            break
        if label:
            row_map[label] = row
        end_index += 1

    code_row = _find_row(row_map, COLUMN_CODE_LABELS)
    type_row = _find_row(row_map, TYPE_LABELS)
    size_row = _find_row(row_map, SIZE_LABELS)
    required_row = _find_row(row_map, REQUIRED_LABELS)
    unique_row = _find_row(row_map, UNIQUE_LABELS)
    key_row = _find_row(row_map, KEY_LABELS)
    reference_row = _find_row(row_map, REFERENCE_LABELS)
    default_row = _find_row(row_map, DEFAULT_LABELS)

    if not code_row or not type_row:
        raise ConfigParseError(f'Для таблицы {table_name} отсутствуют строки с кодами колонок или типами.')

    max_len = max(
        len(code_row),
        len(type_row),
        len(size_row or []),
        len(required_row or []),
        len(unique_row or []),
        len(key_row or []),
        len(reference_row or []),
        len(default_row or []),
    )

    columns: list[ColumnConfig] = []
    for idx in range(1, max_len):
        name = _cell(code_row, idx)
        db_type = _cell(type_row, idx)
        if not name:
            continue
        if not db_type:
            raise ConfigParseError(f'У колонки {name} таблицы {table_name} не указан тип.')

        key_value = (_cell(key_row, idx) or '').lower()
        reference_value = _cell(reference_row, idx)

        if ('references' in key_value or key_value in {'fk', 'foreign key'}) and not reference_value:
            raise ConfigParseError(
                f'Колонка {name} таблицы {table_name}: задан ключ references, '
                'но не указана ссылка на таблицу.'
            )

        columns.append(
            ColumnConfig(
                name=name,
                db_type=db_type,
                size=_cell(size_row, idx),
                nullable=not _contains_any(_cell(required_row, idx), {'not null', 'required', 'обязательно'}),
                unique=_contains_any(_cell(unique_row, idx), {'unique', 'yes', 'true', '1', 'да'}),
                primary_key='primary key' in key_value or key_value == 'pk',
                foreign_key=reference_value if ('references' in key_value or reference_value) else None,
                default=_cell(default_row, idx),
            )
        )

    return TableConfig(name=table_name, columns=columns), end_index


def _find_row(row_map: dict[str, list], names: set[str]) -> list | None:
    for name in names:
        if name in row_map:
            return row_map[name]
    return None


def _cell(row: list | None, index: int) -> str | None:
    if not row or index >= len(row):
        return None
    return _normalize_text(row[index])


def _label(value) -> str:
    return _normalize_text(value, lower=True) or ''


def _normalize_text(value, lower: bool = False) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.lower() if lower else text


def _first_non_empty(values: list) -> str | None:
    for value in values:
        text = _normalize_text(value)
        if text:
            return text
    return None


def _contains_any(value: str | None, expected_values: set[str]) -> bool:
    if not value:
        return False
    lower_value = value.lower()
    return any(item in lower_value for item in expected_values)


def _to_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'да'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'нет'}:
        return False
    return default
