# db_setting_credential_service.py

from datetime import datetime, timezone

from flask import Response, jsonify

from common.context_service import ContextService
from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.db_setting_credential.db_setting_credential_repository import DbSettingCredentialRepository


class DbSettingCredentialService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._repository = DbSettingCredentialRepository()

    def list_credentials(self) -> Response:
        user_id = ContextService.get_user_info().user_id
        rows = self._repository.find_all_with_user_credentials(user_id)
        return jsonify(credentials=[
            {
                'db_setting_id': r[0],
                'db_label': r[1],
                'host': r[2],
                'port': r[3],
                'name': r[4],
                'credential_id': r[5],
                'login': r[6],
            }
            for r in rows
        ])

    def save_credential(self, data: dict) -> Response:
        user = ContextService.get_user_info()
        db_setting_id = data.get('db_setting_id')
        login = (data.get('login') or '').strip()
        password = (data.get('password') or '').strip()

        if not login:
            raise AppError('Не указан логин.')
        if not db_setting_id:
            raise AppError('Не указан идентификатор подключения.')

        credential = self._repository.find_by_user_and_setting(user.user_id, int(db_setting_id))

        if credential is None:
            from domains.db_setting_credential.db_setting_credential_model import DbSettingCredentialModel
            if not password:
                raise AppError('Пароль обязателен при создании учётных данных.')
            credential = DbSettingCredentialModel()
            credential.user_id = user.user_id
            credential.db_setting_id = int(db_setting_id)
            credential.login = login
            credential.password = password
            credential.created_by = user.user_id
        else:
            credential.login = login
            if password:
                credential.password = password
            credential.updated_at = datetime.now(timezone.utc)
            credential.updated_by = user.user_id

        self._repository.save(credential)
        return jsonify(ok=True)
