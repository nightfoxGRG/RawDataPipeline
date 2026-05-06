# context_service.py
"""Сервис контекста пользователя."""

import base64
import json
from sqlalchemy.orm import Session

from flask import g

from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.users.model.user_info_model import UserInfoModel
from domains.users.users_service import UsersService


class ContextService(metaclass=SingletonMeta):
    def __init__(self):
        self._user_service = UsersService()

    @staticmethod
    def get_user_info() -> UserInfoModel:
        user: UserInfoModel | None = getattr(g, 'current_user', None)
        if user is None:
            raise AppError('Пользователь не аутентифицирован.')
        return user

    def load_user_context(self, token: str, session: Session) -> UserInfoModel | None:
        subject_id = self._decode_subject_from_jwt(token)
        if not subject_id:
            return None
        return self._user_service.get_user_info(subject_id, session)

    @staticmethod
    def _pad_base64(value: str) -> str:
        return value + '=' * (-len(value) % 4)

    def _decode_subject_from_jwt(self, token: str) -> str | None:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        try:
            payload = base64.urlsafe_b64decode(self._pad_base64(parts[1]))
            data = json.loads(payload)
        except (ValueError, json.JSONDecodeError):
            return None
        return data.get('sub') or data.get('subject_id')