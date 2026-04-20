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
