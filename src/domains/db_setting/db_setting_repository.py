# db_setting_repository.py
"""Репозиторий настроек подключения к БД."""

from sqlalchemy.orm import Session

from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.db_setting.db_setting_model import DbSettingModel

@repository
class DbSettingRepository(metaclass=SingletonMeta):

    def save(self, db_setting: DbSettingModel) -> DbSettingModel:
        merged = self._session.merge(db_setting)
        self._session.flush()
        return merged
