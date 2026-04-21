import re

from services.models import ColumnConfig, TableConfig
from services.sql_generator import generate_sql


def test_generate_sql_includes_constraints_and_references():
    tables = [
        TableConfig(
            name='test_table',
            columns=[
                ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True),
                ColumnConfig(name='code', db_type='varchar', size='50', nullable=False, unique=True),
                ColumnConfig(name='another_table_id', db_type='bigint', nullable=False, foreign_key='another_table(id)'),
            ],
        )
    ]

    sql = generate_sql(tables)

    assert 'create table test_table' in sql
    assert re.search(r'id\s+bigserial\s+not null\s+primary key', sql)
    assert re.search(r'code\s+varchar\(50\)\s+not null\s+unique', sql)
    assert re.search(r'another_table_id\s+bigint\s+not null\s+references another_table\(id\)', sql)


def test_generate_sql_appends_column_label_as_comment():
    tables = [
        TableConfig(
            name='users',
            columns=[
                ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True, label='Идентификатор'),
                ColumnConfig(name='full_name', db_type='varchar', size='255', label='Полное имя'),
                ColumnConfig(name='age', db_type='integer'),
            ],
        )
    ]

    sql = generate_sql(tables)

    assert re.search(r'id\s+bigserial\s+not null\s+primary key,\s+--\s+Идентификатор', sql)
    assert re.search(r'full_name\s+varchar\(255\),\s+--\s+Полное имя', sql)
    assert re.search(r'age\s+integer', sql)
    # column without label must not have a comment
    assert not re.search(r'age\s+integer\s+--', sql)


def test_generate_sql_aligns_comments_within_table():
    tables = [
        TableConfig(
            name='test_table',
            columns=[
                ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True, label='Ид'),
                ColumnConfig(name='code', db_type='varchar', size='50', nullable=False, label='Код'),
                ColumnConfig(name='name', db_type='varchar', size='250', label='Наименование'),
                ColumnConfig(name='another_table_id', db_type='bigint', nullable=False,
                             foreign_key='another_table(id)', label='Ссылочный ключ'),
            ],
        )
    ]

    sql = generate_sql(tables)
    comment_positions = [
        line.index('--') for line in sql.splitlines() if '--' in line
    ]
    assert len(set(comment_positions)) == 1, (
        f'Comments are not aligned — found positions: {comment_positions}'
    )
    tables = [
        TableConfig(
            name='orders',
            columns=[
                ColumnConfig(name='id', db_type='bigserial', nullable=False, primary_key=True),
                ColumnConfig(name='customer_name', db_type='varchar', size='100', nullable=False),
                ColumnConfig(name='total', db_type='numeric', size='10,2'),
            ],
        )
    ]

    sql = generate_sql(tables)
    lines = [ln for ln in sql.splitlines() if ln.strip() and not ln.strip().startswith('create') and ln.strip() != ');']

    # Each column line: name padded to the same width, then two spaces, then type
    # Extract the positions where the type part starts (after 4-space indent + padded name + 2 spaces)
    col_name_width = len('customer_name')  # longest name
    for line in lines:
        content = line.lstrip()
        col_name = content.split()[0]
        # The name field in each line must be padded to col_name_width
        expected_name_field = col_name.ljust(col_name_width)
        assert line.startswith(f'    {expected_name_field}  '), (
            f'Expected name padded to {col_name_width} chars in: {line!r}'
        )
