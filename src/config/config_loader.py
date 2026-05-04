# config_loader.py
import os
import tomllib
from typing import Any, Dict
from common.project_paths import ProjectPaths

# Кеш для загруженного конфига
_config: Dict[str, Any] | None = None

def get_config() -> Dict[str, Any]:
    """Возвращает текущий конфиг.
    Если конфиг ещё не был загружен, загружает его автоматически.

    Returns:
        Словарь с конфигурацией
    """
    global _config
    if _config is None:
        return _load_config()
    return _config

def reset_config() -> None:
    """Сбросить закешированный конфиг.
    Полезно для тестов, когда нужно перезагрузить конфигурацию.
    """
    global _config
    _config = None

def _load_config(force_reload: bool = False) -> dict:
    """Загрузить конфигурацию.
    При первом вызове читает файлы и кеширует результат.
    При повторных вызовах возвращает закешированный словарь.

    Базовый файл: config/config.toml (хранится в git, без секретов)
    Локальный оверрайд: config/config.local.toml (в .gitignore, секреты)
    config.local.toml применяется только если APP_ENV=local.
    Значения из local перекрывают значения из base (deep merge)

    Args:
        force_reload: если True, принудительно перечитать файлы с диска
    """
    global _config

    # Возвращаем кеш, если он есть и не требуется принудительная перезагрузка
    if _config is not None and not force_reload:
        return _config

    base_path = ProjectPaths.CONFIG / 'config.toml'
    local_path = ProjectPaths.CONFIG / 'config.local.toml'

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

    # Кешируем результат
    _config = cfg
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