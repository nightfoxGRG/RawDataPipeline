# users_service.py
"""Сервис пользователей."""

from common.singleton_meta import SingletonMeta
from domains.users.model.user_info_model import UserInfoModel
from domains.users.users_repository import UsersRepository


class UsersService(metaclass=SingletonMeta):
    def __init__(self):
        self._repository = UsersRepository()

    def get_user_info(self, subject_id: str) -> UserInfoModel | None:
        return self._repository.find_user_info_by_subject_id(subject_id)

    def get_or_create_user(self, subject_id: str, first_name: str, last_name: str, email: str) -> UserInfoModel | None:
        self._repository.upsert_by_subject_id(subject_id, first_name, last_name, email)
        return self._repository.find_user_info_by_subject_id(subject_id)
