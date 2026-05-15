# minio_storage.py
"""Реализация TableConfigStorage поверх MinIO (server-режим)."""
from __future__ import annotations

from common.singleton_meta import SingletonMeta
from domains.minio.minio_service import MinioService


class MinioTableConfigStorage(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._minio = MinioService()

    def upload_bytes(self, bucket: str, name: str, data: bytes, content_type: str = 'application/octet-stream') -> None:
        self._minio.upload_bytes(bucket, name, data, content_type)

    def download_bytes(self, bucket: str, name: str) -> bytes:
        return self._minio.download_bytes(bucket, name)

    def copy_to_bucket(self, src_bucket: str, dst_bucket: str, name: str) -> None:
        self._minio.copy_to_bucket(src_bucket, dst_bucket, name)

    def delete(self, bucket: str, name: str) -> None:
        self._minio.delete(bucket, name)
