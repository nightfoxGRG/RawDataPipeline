# user_setting_service.py
"""Сервис настроек пользователя."""

from datetime import datetime, timezone

from flask import Response, jsonify

from common.context_service import ContextService
from common.singleton_meta import SingletonMeta
from domains.users.model.user_setting_model import UserSettingModel
from domains.users.user_setting_repository import UserSettingRepository


class UserSettingService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._repository = UserSettingRepository()

    def get_actual_project(self) -> Response:
        user_id = ContextService.get_user_info().user_id
        setting = self._repository.find_by_user(user_id)
        return jsonify(actual_project_id=setting.actual_project_id if setting else None)

    def set_actual_project(self, data: dict) -> Response:
        user = ContextService.get_user_info()
        raw = data.get('actual_project_id')
        actual_project_id = int(raw) if raw else None

        setting = self._repository.find_by_user(user.user_id)
        if setting is None:
            setting = UserSettingModel()
            setting.user_id = user.user_id
            setting.created_by = user.user_id
        else:
            setting.updated_at = datetime.now(timezone.utc)
            setting.updated_by = user.user_id

        setting.actual_project_id = actual_project_id
        self._repository.save(setting)
        return jsonify(ok=True)
