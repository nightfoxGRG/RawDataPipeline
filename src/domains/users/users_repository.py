# users_repository.py
"""Репозиторий пользователей."""

from sqlalchemy import text
from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.users.model.user_info_model import UserInfoModel


@repository
class UsersRepository(metaclass=SingletonMeta):

    def upsert_by_subject_id(self, subject_id: str, first_name: str, last_name: str, email: str) -> None:
        self._session.execute(text("""
            INSERT INTO users (subject_id, first_name, last_name, email)
            VALUES (:subject_id, :first_name, :last_name, :email)
            ON CONFLICT (subject_id) WHERE is_tech_user = false
            DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name  = EXCLUDED.last_name,
                email      = EXCLUDED.email,
                updated_at = now()
        """), {'subject_id': subject_id, 'first_name': first_name,
               'last_name': last_name, 'email': email})
        self._session.flush()

    def find_user_info_by_subject_id(self, subject_id: str) -> UserInfoModel | None:
        row = self._session.execute(text("""
            SELECT
                u.id            AS user_id,
                u.subject_id,
                u.first_name,
                u.last_name,
                u.email,
                u.is_tech_user,
                p.id            AS project_id,
                p.code          AS project_code,
                p.schema        AS project_schema,
                p.description   AS project_description,
                db.id           AS db_id,
                db.db_label,
                db.host         AS db_host,
                db.port         AS db_port,
                db.name         AS db_name
            FROM users u
            LEFT JOIN user_setting us ON u.id = us.user_id
            LEFT JOIN project p       ON us.actual_project_id = p.id
            LEFT JOIN db_setting db   ON p.db_setting_id = db.id
            WHERE u.subject_id = :subject_id
            LIMIT 1
        """), {'subject_id': subject_id}).mappings().first()
        return UserInfoModel(**row) if row else None
