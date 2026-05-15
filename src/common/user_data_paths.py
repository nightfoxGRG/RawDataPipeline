# user_data_paths.py
"""Пути к пользовательским данным в local-режиме.

В local-сборке config.local.toml и xlsx-файлы конфигуратора живут в пользовательском
каталоге (.app/.exe read-only), не в bundled-ресурсах:
  macOS/Linux:  ~/.config/DataPipelinePro/
  Windows:      %APPDATA%\\DataPipelinePro\\
"""

import os
import sys
from pathlib import Path


_APP_NAME = 'DataPipelinePro'


def user_data_dir() -> Path:
    """Корневой каталог пользовательских данных."""
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA') or (Path.home() / 'AppData' / 'Roaming'))
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or (Path.home() / '.config'))
    return base / _APP_NAME


def user_config_file() -> Path:
    return user_data_dir() / 'config.local.toml'


def table_config_storage_dir() -> Path:
    return user_data_dir() / 'table_configs'


def ensure_user_data_dir() -> Path:
    """Создать пользовательский каталог если его нет. Вернуть путь."""
    path = user_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path
