# minio_client.py
from minio import Minio

from common.singleton_meta import SingletonMeta
from config.config_loader import get_config


class MinioClient(metaclass=SingletonMeta):
    """Singleton-обёртка над Minio. Создаёт клиент один раз на основе config.toml."""

    def __init__(self) -> None:
        cfg = get_config().get('minio', {})
        self._client = Minio(
            endpoint=cfg.get('endpoint', 'localhost:50002'),
            access_key=cfg.get('access_key', 'minioadmin'),
            secret_key=cfg.get('secret_key', 'minioadmin'),
            secure=cfg.get('secure', False),
        )

    @property
    def client(self) -> Minio:
        return self._client
