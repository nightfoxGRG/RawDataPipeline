# local_file_storage.py
"""Реализация TableConfigStorage поверх локальной ФС (local-режим).

Структура:
  <user_data_dir>/table_configs/<bucket>/<name>

Бакеты — обычные подкаталоги. Объекты — файлы.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from common.error import AppError
from common.singleton_meta import SingletonMeta
from common.user_data_paths import table_config_storage_dir


class LocalFileTableConfigStorage(metaclass=SingletonMeta):

    def _path(self, bucket: str, name: str) -> Path:
        return table_config_storage_dir() / bucket / name

    def _ensure_bucket(self, bucket: str) -> Path:
        path = table_config_storage_dir() / bucket
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upload_bytes(self, bucket: str, name: str, data: bytes, content_type: str = 'application/octet-stream') -> None:
        self._ensure_bucket(bucket)
        target = self._path(bucket, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def download_bytes(self, bucket: str, name: str) -> bytes:
        target = self._path(bucket, name)
        if not target.exists():
            raise AppError(f'Файл "{name}" не найден в хранилище.')
        return target.read_bytes()

    def copy_to_bucket(self, src_bucket: str, dst_bucket: str, name: str) -> None:
        src = self._path(src_bucket, name)
        if not src.exists():
            raise AppError(f'Файл "{name}" не найден в хранилище.')
        self._ensure_bucket(dst_bucket)
        dst = self._path(dst_bucket, name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def delete(self, bucket: str, name: str) -> None:
        target = self._path(bucket, name)
        if target.exists():
            target.unlink()
