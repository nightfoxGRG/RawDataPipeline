# db_setting_credential_repository.py

from sqlalchemy import text as sa_text

from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.db_setting_credential.db_setting_credential_model import DbSettingCredentialModel


@repository
class DbSettingCredentialRepository(metaclass=SingletonMeta):

    def find_all_with_user_credentials(self, user_id: int) -> list[tuple]:
        """Возвращает все db_setting с учётными данными пользователя (LEFT JOIN).
        Columns: db_setting_id, db_label, host, port, name, credential_id, login"""
        rows = self._session.execute(
            sa_text(
                'SELECT s.id, s.db_label, s.host, s.port, s.name, '
                '       c.id AS credential_id, c.login '
                'FROM db_setting s '
                'LEFT JOIN db_setting_credential c '
                '       ON c.db_setting_id = s.id AND c.user_id = :user_id '
                'ORDER BY s.db_label'
            ),
            {'user_id': user_id},
        ).fetchall()
        return rows

    def find_by_user_and_setting(self, user_id: int, db_setting_id: int) -> DbSettingCredentialModel | None:
        from sqlalchemy import and_
        from domains.db_setting_credential.db_setting_credential_model import DbSettingCredentialModel as M
        return (
            self._session.query(M)
            .filter(and_(M.user_id == user_id, M.db_setting_id == db_setting_id))
            .first()
        )

    def find_by_id(self, credential_id: int) -> DbSettingCredentialModel | None:
        return self._session.get(DbSettingCredentialModel, credential_id)

    def save(self, credential: DbSettingCredentialModel) -> DbSettingCredentialModel:
        merged = self._session.merge(credential)
        self._session.flush()
        return merged
