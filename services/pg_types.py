"""PostgreSQL type categorization helpers used by validators and sql_generator."""

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

# SQL keyword constants that must be emitted without quoting
_SQL_KEYWORD_CONSTANTS: frozenset[str] = frozenset({
    'null', 'true', 'false',
    'current_timestamp', 'current_date', 'current_time',
    'localtime', 'localtimestamp',
    'current_user', 'session_user', 'current_catalog', 'current_schema',
})


def _base_type(db_type: str) -> str:
    """Return the base type name without size/precision, normalised to lower-case."""
    return db_type.strip().lower().split('(')[0].strip()


def is_sql_expression(value: str) -> bool:
    """Return True if *value* is a SQL keyword constant or function call (contains '(')."""
    lower = value.strip().lower()
    return lower in _SQL_KEYWORD_CONSTANTS or '(' in lower


def is_numeric_type(db_type: str) -> bool:
    return _base_type(db_type) in _NUMERIC_BASE_TYPES


def is_boolean_type(db_type: str) -> bool:
    return _base_type(db_type) in _BOOLEAN_BASE_TYPES


def is_quoted_type(db_type: str) -> bool:
    """Return True for types whose literal default values must be wrapped in single quotes."""
    return _base_type(db_type) in _QUOTED_BASE_TYPES
