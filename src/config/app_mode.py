# app_mode.py
"""Режим работы приложения: local (PyInstaller-сборка) или server (из исходников)."""

import os
import sys
from enum import Enum


class AppMode(str, Enum):
    LOCAL = 'local'
    SERVER = 'server'


def get_app_mode() -> AppMode:
    """Определить режим работы.

    Приоритет:
      1) APP_MODE env-переменная (для dev-режима, можно форсировать local при запуске из исходников)
      2) sys.frozen → LOCAL (PyInstaller bundle)
      3) SERVER по умолчанию
    """
    env = (os.environ.get('APP_MODE') or '').strip().lower()
    if env in ('local', 'server'):
        return AppMode(env)
    if getattr(sys, 'frozen', False):
        return AppMode.LOCAL
    return AppMode.SERVER


def is_local() -> bool:
    return get_app_mode() == AppMode.LOCAL


def is_server() -> bool:
    return get_app_mode() == AppMode.SERVER
