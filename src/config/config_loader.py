import os
import tomllib

from common.project_paths import ProjectPaths

def load_config() -> dict:
    """Загрузить конфигурацию.
    Базовый файл: config/config.toml (хранится в git, без секретов)
    Локальный оверрайд: config/config.local.toml (в .gitignore, секреты)
    config.local.toml применяется только если APP_ENV=local.
    Значения из local перекрывают значения из base (deep merge)
    """
    base_path =  ProjectPaths.CONFIG /  'config.toml'
    local_path =  ProjectPaths.CONFIG / 'config.local.toml'

    cfg: dict = {}
    if base_path.exists():
        with open(base_path, 'rb') as f:
            cfg = tomllib.load(f)
    else: 
        raise RuntimeError(f"Не найден конфигурационный файл: {base_path.absolute}")

    app_env = os.getenv('APP_ENV', '').lower()

    if app_env == 'local':
        if local_path.exists():
            with open(local_path, 'rb') as f:
                local_cfg = tomllib.load(f)
            cfg = _deep_merge(cfg, local_cfg)
        else: 
            raise RuntimeError(f"Не найден локальный конфигурационный файл: {local_path.absolute}")
    
    return cfg


def _deep_merge(base: dict, override: dict) -> dict:
    """Рекурсивно объединить словари: override перекрывает base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

