# minio_service.py
from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from typing import IO

from minio.commonconfig import CopySource
from minio.error import S3Error

from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.minio.minio_client import MinioClient


class MinioService(metaclass=SingletonMeta):
    """Базовые операции с MinIO: создание бакета, загрузка, скачивание, список, удаление, URL."""

    def __init__(self) -> None:
        self._client = MinioClient().client

    # ── Бакеты ───────────────────────────────────────────────────────────────

    def ensure_bucket(self, bucket_name: str) -> None:
        """Создать бакет, если он ещё не существует."""
        try:
            if not self._client.bucket_exists(bucket_name):
                self._client.make_bucket(bucket_name)
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка при создании бакета "{bucket_name}": {exc}') from exc

    # ── Загрузка ─────────────────────────────────────────────────────────────

    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = 'application/octet-stream',
    ) -> None:
        """Загрузить bytes-объект в MinIO."""
        self.ensure_bucket(bucket_name)
        try:
            self._client.put_object(
                bucket_name,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка загрузки "{object_name}": {exc}') from exc

    def upload_stream(
        self,
        bucket_name: str,
        object_name: str,
        stream: IO[bytes],
        length: int = -1,
        content_type: str = 'application/octet-stream',
    ) -> None:
        """Загрузить произвольный файловый поток в MinIO.

        Передайте length=-1 для потокового режима (потребует part_size).
        """
        self.ensure_bucket(bucket_name)
        kwargs: dict = dict(content_type=content_type)
        if length == -1:
            kwargs['part_size'] = 10 * 1024 * 1024  # 10 МБ
        try:
            self._client.put_object(bucket_name, object_name, stream, length, **kwargs)
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка загрузки "{object_name}": {exc}') from exc

    # ── Скачивание ───────────────────────────────────────────────────────────

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Скачать объект и вернуть его содержимое как bytes."""
        try:
            response = self._client.get_object(bucket_name, object_name)
            return response.read()
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка скачивания "{object_name}": {exc}') from exc

    # ── Список объектов ──────────────────────────────────────────────────────

    def list_objects(
        self,
        bucket_name: str,
        prefix: str = '',
        recursive: bool = True,
    ) -> list[str]:
        """Вернуть список имён объектов в бакете (с опциональным префиксом)."""
        try:
            objects = self._client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
            return [obj.object_name for obj in objects]
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка получения списка объектов: {exc}') from exc

    # ── Копирование ──────────────────────────────────────────────────────────

    def copy_to_bucket(self, src_bucket: str, dst_bucket: str, object_name: str) -> None:
        """Скопировать объект из src_bucket в dst_bucket (имя объекта сохраняется)."""
        self.ensure_bucket(dst_bucket)
        try:
            self._client.copy_object(dst_bucket, object_name, CopySource(src_bucket, object_name))
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка копирования "{object_name}": {exc}') from exc

    # ── Удаление ─────────────────────────────────────────────────────────────

    def delete(self, bucket_name: str, object_name: str) -> None:
        """Удалить объект из бакета."""
        try:
            self._client.remove_object(bucket_name, object_name)
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка удаления "{object_name}": {exc}') from exc

    # ── Временные ссылки ─────────────────────────────────────────────────────

    def presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_hours: int = 1,
    ) -> str:
        """Сгенерировать временную ссылку для скачивания объекта."""
        try:
            return self._client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(hours=expires_hours),
            )
        except S3Error as exc:
            raise AppError(f'MinIO: ошибка генерации ссылки для "{object_name}": {exc}') from exc
