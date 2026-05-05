# db_setting_repository.py
"""Репозиторий настроек подключения к БД."""

from sqlalchemy.orm import Session

from common.singleton_meta import SingletonMeta
from domains.db_setting.db_setting_model import DbSettingModel


class DbSettingRepository(metaclass=SingletonMeta):

    def save(self, db_setting: DbSettingModel, session: Session) -> DbSettingModel:
        merged = session.merge(db_setting)
        session.flush()
        return merged
