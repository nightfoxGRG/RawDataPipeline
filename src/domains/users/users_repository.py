# users_repository.py
"""Репозиторий пользователей."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from domains.users.model.user_info_model import UserInfoModel

class UsersRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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
                p.schema        AS project_schema,
                p.description   AS project_description,
                db.id           AS db_id,
                db.db_label
            FROM users u
            LEFT JOIN user_setting us ON u.id = us.user_id
            LEFT JOIN project p       ON us.actual_project_id = p.id
            LEFT JOIN db_setting db   ON us.actual_db_setting_id = db.id
            WHERE u.subject_id = :subject_id
            LIMIT 1
        """), {'subject_id': subject_id}).mappings().first()
        return UserInfoModel(**row) if row else None
