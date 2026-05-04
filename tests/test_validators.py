# test_validators.py
import pytest

from common.error import ValidationError
from domains.table_config.table_config_validator import TableConfigValidator
from domains.table_config.table_config_model import TableConfig, ColumnConfig

_validator = TableConfigValidator()


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

    with pytest.raises(ValidationError) as exc_info:
        _validator.validate_tables(tables)
    errors = exc_info.value.errors

    assert any('зарезервированное слово' in error for error in errors)
    assert any('дубликат колонки' in error for error in errors)
    assert any('дубликат таблицы' in error for error in errors)
    assert any('недопустимые символы' in error for error in errors)


def test_validate_tables_accepts_valid_config():
    tables = [
        TableConfig(
            name='customer_data',
            columns=[
                ColumnConfig(name='id', db_type='bigserial', primary_key=True, nullable=False),
                ColumnConfig(name='name', db_type='varchar'),
                ColumnConfig(name='region_id', db_type='bigint', foreign_key='regions(id)'),
            ],
        )
    ]

    _validator.validate_tables(tables)


def test_validate_default_string_type_is_always_valid():
    tables = [
        TableConfig(
            name='t',
            columns=[
                ColumnConfig(name='msg', db_type='varchar', default='Hello world'),
                ColumnConfig(name='note', db_type='text', default='any text'),
            ],
        )
    ]
    _validator.validate_tables(tables)


def test_validate_default_valid_number_for_numeric_type():
    tables = [
        TableConfig(
            name='t',
            columns=[
                ColumnConfig(name='score', db_type='integer', default='0'),
                ColumnConfig(name='ratio', db_type='numeric', default='3.14'),
                ColumnConfig(name='amount', db_type='bigint', default='-1'),
            ],
        )
    ]
    _validator.validate_tables(tables)


def test_validate_default_invalid_number_for_numeric_type():
    tables = [
        TableConfig(
            name='t',
            columns=[
                ColumnConfig(name='score', db_type='integer', default='hello'),
            ],
        )
    ]
    with pytest.raises(ValidationError) as exc_info:
        _validator.validate_tables(tables)
    errors = exc_info.value.errors
    assert any('значение по умолчанию' in e and 'hello' in e for e in errors)


def test_validate_default_sql_expressions_are_always_valid():
    tables = [
        TableConfig(
            name='t',
            columns=[
                ColumnConfig(name='c1', db_type='timestamp', default='now()'),
                ColumnConfig(name='c2', db_type='date', default='CURRENT_DATE'),
                ColumnConfig(name='c3', db_type='boolean', default='true'),
                ColumnConfig(name='c4', db_type='integer', default='NULL'),
            ],
        )
    ]
    _validator.validate_tables(tables)


def test_validate_default_invalid_for_boolean_type():
    tables = [
        TableConfig(
            name='t',
            columns=[
                ColumnConfig(name='flag', db_type='boolean', default='да'),
            ],
        )
    ]
    with pytest.raises(ValidationError) as exc_info:
        _validator.validate_tables(tables)
    errors = exc_info.value.errors
    assert any('значение по умолчанию' in e and 'boolean' in e for e in errors)
