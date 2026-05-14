# project_repository.py
"""Репозиторий проектов."""

from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.project.project_model import ProjectModel


@repository
class ProjectRepository(metaclass=SingletonMeta):

    def find_all(self) -> list[ProjectModel]:
        return self._session.query(ProjectModel).order_by(ProjectModel.code).all()

    def find_by_id(self, project_id: int) -> ProjectModel | None:
        return self._session.get(ProjectModel, project_id)

    def save(self, project: ProjectModel) -> ProjectModel:
        merged = self._session.merge(project)
        self._session.flush()
        return merged

    def delete(self, project_id: int) -> None:
        project = self._session.get(ProjectModel, project_id)
        if project:
            self._session.delete(project)
            self._session.flush()
