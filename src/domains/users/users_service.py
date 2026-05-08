# users_service.py
"""Сервис пользователей."""

from sqlalchemy.orm import Session

from common.singleton_meta import SingletonMeta
from domains.users.model.user_info_model import UserInfoModel
from domains.users.users_repository import UsersRepository


class UsersService(metaclass=SingletonMeta):
    def __init__(self):
        self._repository = UsersRepository()

    def get_user_info(self, subject_id: str) -> UserInfoModel | None:
        return self._repository.find_user_info_by_subject_id(subject_id)
