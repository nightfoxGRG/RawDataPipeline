# system_db_config.py
#system_db_config
from config.config_loader import get_config

_db_urls: dict[str | None, str] = {}
_DB_SYSTEM_SCHEMA: str = "data_pipline_schema"
_db_system_schema_override: str | None = None


def _build_url(driver: str | None = None) -> str:
    cfg = get_config()
    db = cfg.get('database', {})
    host = db.get('host')
    port = db.get('port')
    name = db.get('name')
    user = db.get('user')
    password = db.get('password', '')

    scheme = 'postgresql'
    if driver:
        scheme = f'{scheme}+{driver}'

    auth = ''
    if user:
        auth = user
        if password:
            auth = f'{auth}:{password}'
        auth = f'{auth}@'

    db_url = f'{scheme}://{auth}{host}:{port}/{name}'
    return db_url


def get_db_url(driver: str | None = None) -> str:
    global _db_urls
    if driver in _db_urls:
        return _db_urls[driver]

    db_url = _build_url(driver)
    _db_urls[driver] = db_url
    return db_url

def get_db_system_schema() -> str:
    if _db_system_schema_override:
        return _db_system_schema_override
    try:
        cfg = get_config()
        schema = cfg.get('database', {}).get('schema')
        if schema:
            return schema
    except Exception:
        pass
    return _DB_SYSTEM_SCHEMA


def reset_db_urls() -> None:
    """Сбросить кеш URL-ов (после изменения config)."""
    global _db_urls, _db_system_schema_override
    _db_urls = {}
    _db_system_schema_override = None