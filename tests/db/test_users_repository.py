# test_users_repository.py
from sqlalchemy import text

from domains.db_setting.db_setting_repository import DbSettingRepository
from domains.project.project_repository import ProjectRepository
from domains.users.model.user_info_model import UserInfoModel
from domains.users.model.users_model import UsersModel  # регистрирует таблицу users в metadata
from domains.users.user_setting_repository import UserSettingRepository
from domains.users.users_repository import UsersRepository
from tests.db.postgres_container_base import PostgresContainerBase


class TestUsersRepositoryFindBySubjectId(PostgresContainerBase):

    def setup_method(self) -> None:
        super().setup_method()

        row = self.session.execute(text("SELECT id FROM users WHERE subject_id = 'TECH_USER'")).first()
        self._tech_user_id = row[0]

        row = self.session.execute(text("SELECT id FROM users WHERE subject_id = 'LOCAL_USER'")).first()
        self._local_user_id = row[0]

    # ------------------------------------------------------------------
    # Пользователь без настроек
    # ------------------------------------------------------------------

    def test_returns_user_info_for_existing_user(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result is not None
        assert isinstance(result, UserInfoModel)

    def test_correct_user_fields(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result.subject_id == 'LOCAL_USER'
        assert result.first_name == 'Локальный пользователь'
        assert result.is_tech_user is True
        assert result.last_name is None
        assert result.email is None

    def test_project_and_db_are_none_without_settings(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result.project_id is None
        assert result.project_schema is None
        assert result.project_description is None
        assert result.db_id is None
        assert result.db_label is None

    def test_returns_none_for_nonexistent_subject_id(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('NONEXISTENT_USER')

        assert result is None

    def test_user_id_is_positive_integer(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert isinstance(result.user_id, int)
        assert result.user_id > 0

    # ------------------------------------------------------------------
    # Пользователь с проектом и подключением к БД
    # ------------------------------------------------------------------

    def _insert_test_data(self) -> tuple[int, int]:
        """Вставить проект и db_setting, связать с LOCAL_USER. Вернуть (project_id, db_id)."""
        from domains.project.project_model import ProjectModel
        from domains.db_setting.db_setting_model import DbSettingModel
        from domains.users.model.user_setting_model import UserSettingModel

        project = ProjectRepository().save(ProjectModel(
            schema='test_schema',
            description='Тестовый проект',
            created_by=self._tech_user_id,

        ))
        db_setting = DbSettingRepository().save(DbSettingModel(
            user_id=self._local_user_id,
            db_label='test_db',
            host='localhost',
            port=5432,
            name='testdb',
            db_user='user',
            password='secret',
            created_by=self._tech_user_id,
        ))
        UserSettingRepository().save(UserSettingModel(
            user_id=self._local_user_id,
            actual_project_id=project.id,
            created_by=self._tech_user_id,
        ))
        return project.id, db_setting.id

    def test_returns_project_fields_when_settings_exist(self):
        project_id, _ = self._insert_test_data()
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result.project_id == project_id
        assert result.project_schema == 'test_schema'
        assert result.project_description == 'Тестовый проект'

    def test_returns_db_fields_when_settings_exist(self):
        _, db_id = self._insert_test_data()
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result.db_id == db_id
        assert result.db_label == 'test_db'

    def test_user_fields_unchanged_after_settings_insert(self):
        self._insert_test_data()
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('LOCAL_USER')

        assert result.subject_id == 'LOCAL_USER'
        assert result.is_tech_user is True

    def test_tech_user_is_found(self):
        repo = UsersRepository()

        result = repo.find_user_info_by_subject_id('TECH_USER')

        assert result is not None
        assert result.subject_id == 'TECH_USER'
        assert result.is_tech_user is True
