# system_db_config.py
#system_db_config
from config.config_loader import get_config

_db_url: str | None = None
_DB_SYSTEM_SCHEMA: str  = "data_pipline_schema"

def _build_url() -> str:
    global _db_url
    cfg = get_config()
    db = cfg.get('database', {})
    host = db.get('host')
    port = db.get('port')
    name = db.get('name')
    user = db.get('user')
    password = db.get('password', '')
    db_url =  f'postgresql://{user}:{password}@{host}:{port}/{name}'
    _db_url = db_url
    return _db_url


def get_db_url() -> str:
    global _db_url
    if _db_url is None:
        return _build_url()
    return _db_url

def get_db_system_schema() -> str:
    return _DB_SYSTEM_SCHEMA