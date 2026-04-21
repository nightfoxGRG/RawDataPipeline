"""Generate an Excel configuration file in tables_config_v2 format
from a list of inferred column descriptors.
"""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


_V2_HEADERS = [
    'Описание',
    'Код колонки в БД',
    'Тип',
    'Размерность',
    'Обязательность',
    'Уникальность',
    'Первичный ключ',
    'Внешний ключ',
    'Значение по умолчанию',
]

# Approximate column widths (characters) for each header
_COL_WIDTHS = [20, 20, 14, 12, 14, 12, 14, 25, 22]

_HEADER_FILL = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
_TABLE_FILL = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid')


def generate_excel_config_v2(table_name: str, columns: list[dict]) -> bytes:
    """Build and return bytes of an xlsx workbook containing a tables_config_v2 sheet.

    Each dict in *columns* must contain at least:
      'code'    – column code (SQL identifier)
      'db_type' – PostgreSQL type
    Optional keys: 'label', 'size'.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'tables_config_v2'

    # ----- Row 1: table name -----
    name_cell = ws.cell(row=1, column=1, value=table_name)
    name_cell.font = Font(bold=True)
    name_cell.fill = _TABLE_FILL
    name_cell.alignment = Alignment(horizontal='left', vertical='center')

    # ----- Row 2: headers -----
    for col_idx, header in enumerate(_V2_HEADERS, start=1):
        cell = ws.cell(row=2, column=col_idx, value=header)
        cell.font = Font(bold=True)
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # ----- Rows 3+: column data -----
    for row_idx, col_info in enumerate(columns, start=3):
        ws.cell(row=row_idx, column=1, value=col_info.get('label') or col_info['code'])
        ws.cell(row=row_idx, column=2, value=col_info['code'])
        ws.cell(row=row_idx, column=3, value=col_info['db_type'])
        size = col_info.get('size')
        if size:
            ws.cell(row=row_idx, column=4, value=size)

    # ----- Column widths -----
    for col_idx, width in enumerate(_COL_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    # ----- Freeze panes below header row -----
    ws.freeze_panes = 'A3'

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
