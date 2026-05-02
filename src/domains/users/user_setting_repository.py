# user_setting_repository.py
"""Репозиторий настроек пользователя."""

from sqlalchemy.orm import Session

from domains.users.model.user_setting_model import UserSettingModel


class UserSettingRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user_setting: UserSettingModel) -> UserSettingModel:
        merged = self._session.merge(user_setting)
        self._session.flush()
        return merged
