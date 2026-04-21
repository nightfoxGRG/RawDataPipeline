from io import BytesIO

import pytest
from openpyxl import Workbook

from services.parser import ConfigParseError, parse_tables_config


def test_parse_excel_tables_config_like_template():
    wb = Workbook()
    ws = wb.active
    ws.title = 'tables_config'

    ws['A1'] = 'Наименование таблицы'
    ws['B1'] = 'test_table'
    ws['A2'] = 'Наименование колонки'
    ws['B2'] = 'Идентификатор'
    ws['C2'] = 'Код'
    ws['D2'] = 'ID другой таблицы'
    ws['A3'] = 'Код колонки в БД'
    ws['B3'] = 'id'
    ws['C3'] = 'code'
    ws['D3'] = 'another_table_id'
    ws['A4'] = 'Тип'
    ws['B4'] = 'bigserial'
    ws['C4'] = 'varchar'
    ws['D4'] = 'bigint'
    ws['A5'] = 'Размерность'
    ws['C5'] = '50'
    ws['A6'] = 'Обязательность'
    ws['B6'] = 'not null'
    ws['C6'] = 'not null'
    ws['D6'] = 'not null'
    ws['A8'] = 'Ключ'
    ws['B8'] = 'primary key'
    ws['D8'] = 'references'
    ws['A9'] = 'Ссылка на таблицу'
    ws['D9'] = 'another_table(id)'

    payload = BytesIO()
    wb.save(payload)

    tables = parse_tables_config(payload.getvalue(), 'config.xlsx')

    assert len(tables) == 1
    assert tables[0].name == 'test_table'
    assert [c.name for c in tables[0].columns] == ['id', 'code', 'another_table_id']
    assert tables[0].columns[1].size == '50'
    assert tables[0].columns[0].primary_key is True
    assert tables[0].columns[2].foreign_key == 'another_table(id)'
    assert tables[0].columns[0].label == 'Идентификатор'
    assert tables[0].columns[1].label == 'Код'
    assert tables[0].columns[2].label == 'ID другой таблицы'


def test_parse_excel_references_key_without_reference_raises_error():
    wb = Workbook()
    ws = wb.active
    ws.title = 'tables_config'

    ws['A1'] = 'Наименование таблицы'
    ws['B1'] = 'test_table'
    ws['A3'] = 'Код колонки в БД'
    ws['B3'] = 'id'
    ws['C3'] = 'fk_col'
    ws['A4'] = 'Тип'
    ws['B4'] = 'bigserial'
    ws['C4'] = 'bigint'
    ws['A8'] = 'Ключ'
    ws['C8'] = 'references'
    # no value in 'Ссылка на таблицу' row for fk_col

    payload = BytesIO()
    wb.save(payload)

    with pytest.raises(ConfigParseError, match='ключ references'):
        parse_tables_config(payload.getvalue(), 'config.xlsx')


def test_parse_excel_da_net_for_required_and_unique():
    wb = Workbook()
    ws = wb.active
    ws.title = 'tables_config'

    ws['A1'] = 'Наименование таблицы'
    ws['B1'] = 'orders'
    ws['A3'] = 'Код колонки в БД'
    ws['B3'] = 'id'
    ws['C3'] = 'code'
    ws['D3'] = 'note'
    ws['A4'] = 'Тип'
    ws['B4'] = 'bigserial'
    ws['C4'] = 'varchar'
    ws['D4'] = 'text'
    ws['A6'] = 'Обязательность'
    ws['B6'] = 'да'   # required → nullable=False
    ws['C6'] = 'нет'  # not required → nullable=True
    # D6 empty → nullable=True (default)
    ws['A7'] = 'Уникальность'
    ws['B7'] = 'нет'  # not unique
    ws['C7'] = 'да'   # unique=True
    # D7 empty → unique=False (default)

    payload = BytesIO()
    wb.save(payload)

    tables = parse_tables_config(payload.getvalue(), 'config.xlsx')

    assert len(tables) == 1
    cols = {c.name: c for c in tables[0].columns}

    assert cols['id'].nullable is False   # Обязательность = "да"
    assert cols['id'].unique is False     # Уникальность = "нет"

    assert cols['code'].nullable is True  # Обязательность = "нет"
    assert cols['code'].unique is True    # Уникальность = "да"

    assert cols['note'].nullable is True  # Обязательность empty
    assert cols['note'].unique is False   # Уникальность empty
