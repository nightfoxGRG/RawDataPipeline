# db_setting_service.py
"""Сервис настроек подключения к БД."""

from datetime import datetime, timezone

from flask import Response, jsonify

from common.context_service import ContextService
from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.db_setting.db_setting_model import DbSettingModel
from domains.db_setting.db_setting_repository import DbSettingRepository


class DbSettingService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._repository = DbSettingRepository()

    def list_settings(self) -> Response:
        settings = self._repository.find_all()
        return jsonify(settings=[self._to_dict(s) for s in settings])

    def save_setting(self, data: dict) -> Response:
        user = ContextService.get_user_info()
        db_label = (data.get('db_label') or '').strip()
        host = (data.get('host') or '').strip()
        port_raw = data.get('port')
        name = (data.get('name') or '').strip()
        setting_id = data.get('id')

        if not db_label:
            raise AppError('Не указано наименование подключения.')
        if not host:
            raise AppError('Не указан хост.')
        if not name:
            raise AppError('Не указано имя базы данных.')
        try:
            port = int(port_raw)
            if port < 1 or port > 65535:
                raise ValueError
        except (TypeError, ValueError):
            raise AppError('Некорректный порт (1–65535).')

        if setting_id:
            model = self._repository.find_by_id(int(setting_id))
            if not model:
                raise AppError('Настройка не найдена.')
            model.db_label = db_label
            model.host = host
            model.port = port
            model.name = name
            model.updated_at = datetime.now(timezone.utc)
            model.updated_by = user.user_id
        else:
            model = DbSettingModel(
                db_label=db_label,
                host=host,
                port=port,
                name=name,
                created_by=user.user_id,
            )

        saved = self._repository.save(model)
        return jsonify(setting=self._to_dict(saved))

    def delete_setting(self, setting_id: int) -> Response:
        model = self._repository.find_by_id(setting_id)
        if not model:
            raise AppError('Настройка не найдена.')
        self._repository.delete(setting_id)
        return jsonify(ok=True)

    @staticmethod
    def _to_dict(s: DbSettingModel) -> dict:
        return {
            'id': s.id,
            'db_label': s.db_label,
            'host': s.host,
            'port': s.port,
            'name': s.name,
        }
