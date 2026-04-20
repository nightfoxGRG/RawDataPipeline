from services.models import ColumnConfig, TableConfig
from services.validators import validate_tables


def test_validate_tables_detects_duplicates_and_reserved_words():
    tables = [
        TableConfig(
            name='select',
            columns=[
                ColumnConfig(name='id', db_type='bigserial'),
                ColumnConfig(name='id', db_type='varchar'),
                ColumnConfig(name='bad-name', db_type='varchar'),
            ],
        ),
        TableConfig(name='select', columns=[ColumnConfig(name='code', db_type='varchar')]),
    ]

    errors = validate_tables(tables)

    assert any('зарезервированное слово' in error for error in errors)
    assert any('дубликат колонки' in error for error in errors)
    assert any('дубликат таблицы' in error for error in errors)
    assert any('недопустимые символы' in error for error in errors)
