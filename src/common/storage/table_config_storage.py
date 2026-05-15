# table_config_storage.py
"""Абстракция хранилища xlsx-файлов конфигуратора.

В server-режиме это MinIO; в local-режиме — файловая система пользовательского каталога.
Интерфейс совпадает с подмножеством MinioService — миграция сервисов в одну строку.
"""
from __future__ import annotations

from typing import Protocol

from common.singleton_meta import SingletonMeta
from config.app_mode import AppMode, get_app_mode


class TableConfigStorage(Protocol):
    def upload_bytes(self, bucket: str, name: str, data: bytes, content_type: str = 'application/octet-stream') -> None: ...
    def download_bytes(self, bucket: str, name: str) -> bytes: ...
    def copy_to_bucket(self, src_bucket: str, dst_bucket: str, name: str) -> None: ...
    def delete(self, bucket: str, name: str) -> None: ...


class TableConfigStorageFactory(metaclass=SingletonMeta):
    """Возвращает storage соответствующий текущему режиму. Кешируется."""

    def __init__(self) -> None:
        self._impl: TableConfigStorage | None = None

    def get(self) -> TableConfigStorage:
        if self._impl is None:
            if get_app_mode() == AppMode.LOCAL:
                from common.storage.local_file_storage import LocalFileTableConfigStorage
                self._impl = LocalFileTableConfigStorage()
            else:
                from common.storage.minio_storage import MinioTableConfigStorage
                self._impl = MinioTableConfigStorage()
        return self._impl


def get_table_config_storage() -> TableConfigStorage:
    return TableConfigStorageFactory().get()
