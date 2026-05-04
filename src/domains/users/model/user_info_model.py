# user_info_model.py
"""DTO: агрегированная информация пользователя."""

from dataclasses import dataclass


@dataclass
class UserInfoModel:
    # users
    user_id: int
    subject_id: str
    first_name: str | None
    last_name: str | None
    email: str | None
    is_tech_user: bool

    # project
    project_id: int | None
    project_schema: str | None
    project_description: str | None

    # db_setting
    db_id: int | None
    db_label: str | None
    db_host: str | None
    db_port: str | None
    db_name: str | None