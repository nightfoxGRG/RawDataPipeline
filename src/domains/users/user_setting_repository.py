# user_setting_repository.py
"""Репозиторий настроек пользователя."""

from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.users.model.user_setting_model import UserSettingModel


@repository
class UserSettingRepository(metaclass=SingletonMeta):

    def find_by_user(self, user_id: int) -> UserSettingModel | None:
        return (
            self._session.query(UserSettingModel)
            .filter(UserSettingModel.user_id == user_id)
            .first()
        )

    def save(self, user_setting: UserSettingModel) -> UserSettingModel:
        merged = self._session.merge(user_setting)
        self._session.flush()
        return merged
