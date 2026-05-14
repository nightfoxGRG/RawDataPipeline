# db_setting_repository.py
"""Репозиторий настроек подключения к БД."""

from dataclasses import dataclass

from sqlalchemy import text as sa_text

from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.db_setting.db_setting_model import DbSettingModel


@dataclass
class DbConnectionInfo:
    host: str
    port: int
    name: str
    login: str
    password: str


@repository
class DbSettingRepository(metaclass=SingletonMeta):

    def find_all(self) -> list[DbSettingModel]:
        return self._session.query(DbSettingModel).order_by(DbSettingModel.db_label).all()

    def find_by_id(self, db_setting_id: int) -> DbSettingModel | None:
        return self._session.get(DbSettingModel, db_setting_id)

    def save(self, db_setting: DbSettingModel) -> DbSettingModel:
        merged = self._session.merge(db_setting)
        self._session.flush()
        return merged

    def delete(self, db_setting_id: int) -> None:
        obj = self._session.get(DbSettingModel, db_setting_id)
        if obj:
            self._session.delete(obj)
            self._session.flush()

    def find_connection_info(self, db_id: int, user_id: int) -> DbConnectionInfo | None:
        row = self._session.execute(
            sa_text(
                'SELECT s.host, s.port, s.name, c.login, c.password '
                'FROM db_setting s '
                'JOIN db_setting_credential c '
                '  ON c.db_setting_id = s.id AND c.user_id = :user_id '
                'WHERE s.id = :db_id'
            ),
            {'db_id': db_id, 'user_id': user_id},
        ).fetchone()
        if row is None:
            return None
        return DbConnectionInfo(host=row[0], port=row[1], name=row[2], login=row[3], password=row[4])
