# postgres_types.py
"""PostgreSQL type categorization helpers used by validators and sql_generator."""
import re

_NUMERIC_BASE_TYPES: frozenset[str] = frozenset({
    'smallint', 'integer', 'int', 'int2', 'int4', 'int8', 'bigint',
    'decimal', 'numeric', 'real', 'float', 'float4', 'float8',
    'double precision', 'money', 'serial', 'bigserial', 'smallserial',
})

_BOOLEAN_BASE_TYPES: frozenset[str] = frozenset({'boolean', 'bool'})

_QUOTED_BASE_TYPES: frozenset[str] = frozenset({
    # textual types
    'varchar', 'character varying', 'char', 'character', 'text', 'name',
    'citext', 'uuid', 'json', 'jsonb', 'xml', 'bytea', 'inet', 'cidr',
    'macaddr', 'macaddr8', 'tsvector', 'tsquery',
    # date/time types
    'date', 'time', 'timetz', 'timestamp', 'timestamptz',
    'time without time zone', 'time with time zone',
    'timestamp without time zone', 'timestamp with time zone',
    'interval',
})

_ALLOWED_BASE_TYPES: frozenset[str] = (
    _NUMERIC_BASE_TYPES | _BOOLEAN_BASE_TYPES | _QUOTED_BASE_TYPES
)

# SQL keyword constants that must be emitted without quoting
_SQL_KEYWORD_CONSTANTS: frozenset[str] = frozenset({
    'null', 'true', 'false',
    'current_timestamp', 'current_date', 'current_time',
    'localtime', 'localtimestamp',
    'current_user', 'session_user', 'current_catalog', 'current_schema',
})

# Допустим только вызов функции без аргументов: now(), gen_random_uuid() и т.п.
# Аргументы запрещены, чтобы исключить инъекцию через содержимое скобок.
_FUNCTION_CALL_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*\(\s*\)$')


def _base_type(db_type: str) -> str:
    """Return the base type name without size/precision, normalised to lower-case."""
    return db_type.strip().lower().split('(')[0].strip()


def looks_like_sql_expression(value: str) -> bool:
    """True если значение похоже на SQL-выражение (keyword или вызов со скобками).

    Используется для разветвления логики: «обработать как SQL-выражение» vs
    «обработать как литерал». Само значение может быть небезопасным —
    проверяйте через ``is_safe_default_expression``.
    """
    lower = value.strip().lower()
    return lower in _SQL_KEYWORD_CONSTANTS or '(' in lower


def is_safe_default_expression(value: str) -> bool:
    """Whitelist допустимых SQL-выражений для DEFAULT.

    Допустимы:
      * keyword-константы из ``_SQL_KEYWORD_CONSTANTS``;
      * вызовы функций без аргументов: ``name()``.

    Произвольные функции с аргументами не пропускаются: их содержимое
    подставляется в DDL как есть и может содержать инъекцию.
    """
    stripped = value.strip()
    if stripped.lower() in _SQL_KEYWORD_CONSTANTS:
        return True
    return bool(_FUNCTION_CALL_RE.match(stripped))


def is_known_db_type(db_type: str) -> bool:
    return _base_type(db_type) in _ALLOWED_BASE_TYPES


def is_numeric_type(db_type: str) -> bool:
    return _base_type(db_type) in _NUMERIC_BASE_TYPES


def is_boolean_type(db_type: str) -> bool:
    return _base_type(db_type) in _BOOLEAN_BASE_TYPES


def is_quoted_type(db_type: str) -> bool:
    """Return True for types whose literal default values must be wrapped in single quotes."""
    return _base_type(db_type) in _QUOTED_BASE_TYPES
