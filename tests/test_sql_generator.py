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
    assert 'id bigserial not null primary key' in sql
    assert 'code varchar(50) not null unique' in sql
    assert 'another_table_id bigint not null references another_table(id)' in sql


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

    assert 'id bigserial not null primary key -- Идентификатор' in sql
    assert 'full_name varchar(255) -- Полное имя' in sql
    assert 'age integer' in sql
    # column without label must not have a comment
    assert 'age integer --' not in sql
