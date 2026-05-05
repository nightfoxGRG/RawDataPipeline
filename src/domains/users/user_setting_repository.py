# user_setting_repository.py
"""Репозиторий настроек пользователя."""

from sqlalchemy.orm import Session

from common.singleton_meta import SingletonMeta
from domains.users.model.user_setting_model import UserSettingModel


class UserSettingRepository(metaclass=SingletonMeta):

    def save(self, user_setting: UserSettingModel, session: Session) -> UserSettingModel:
        merged = session.merge(user_setting)
        session.flush()
        return merged
