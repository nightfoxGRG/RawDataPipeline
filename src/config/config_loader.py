# config_loader.py
import os
import tomllib
from pathlib import Path
from typing import Any, Dict

from common.project_paths import ProjectPaths
from common.user_data_paths import user_config_file
from config.app_mode import AppMode, get_app_mode


class ConfigMissingError(RuntimeError):
    """Локальный config-файл не найден (или незавершённый onboarding)."""


# Кеш для загруженного конфига
_config: Dict[str, Any] | None = None


def get_config() -> Dict[str, Any]:
    """Возвращает текущий конфиг.
    Если конфиг ещё не был загружен, загружает его автоматически.
    """
    global _config
    if _config is None:
        return _load_config()
    return _config


def reset_config() -> None:
    """Сбросить закешированный конфиг (например, после onboarding-сохранения)."""
    global _config
    _config = None


def local_config_path() -> Path:
    """Путь к локальному config-оверрайду.

    В local-режиме — пользовательский каталог (~/.config/DataPipelinePro/).
    В server-режиме (APP_ENV=local при запуске из исходников) — resources/config.local.toml.
    """
    if get_app_mode() == AppMode.LOCAL:
        return user_config_file()
    return ProjectPaths.CONFIG / 'config.local.toml'


def _load_config(force_reload: bool = False) -> dict:
    """Загрузить конфигурацию.

    Базовый файл: resources/config.toml (всегда читается)
    Локальный оверрайд:
      - LOCAL mode  → ~/.config/DataPipelinePro/config.local.toml (обязательный)
      - SERVER mode → resources/config.local.toml (если APP_ENV=local)
    Значения из local перекрывают значения из base (deep merge).
    """
    global _config
    if _config is not None and not force_reload:
        return _config

    base_path = ProjectPaths.CONFIG / 'config.toml'
    if not base_path.exists():
        raise RuntimeError(f'Не найден конфигурационный файл: {base_path}')
    with open(base_path, 'rb') as f:
        cfg = tomllib.load(f)

    mode = get_app_mode()

    if mode == AppMode.LOCAL:
        local_path = user_config_file()
        if not local_path.exists():
            raise ConfigMissingError(f'Локальный config не найден: {local_path}')
        with open(local_path, 'rb') as f:
            cfg = _deep_merge(cfg, tomllib.load(f))
    else:
        # server: легаси-поведение, оверрайд через APP_ENV=local
        if (os.getenv('APP_ENV') or '').lower() == 'local':
            local_path = ProjectPaths.CONFIG / 'config.local.toml'
            if not local_path.exists():
                raise RuntimeError(f'Не найден локальный конфигурационный файл: {local_path}')
            with open(local_path, 'rb') as f:
                cfg = _deep_merge(cfg, tomllib.load(f))

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
