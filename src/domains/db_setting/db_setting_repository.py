# db_setting_repository.py
"""Репозиторий настроек подключения к БД."""

from sqlalchemy.orm import Session

from domains.db_setting.db_setting_model import DbSettingModel


class DbSettingRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, db_setting: DbSettingModel) -> DbSettingModel:
        merged = self._session.merge(db_setting)
        self._session.flush()
        return merged
