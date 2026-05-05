# project_repository.py
"""Репозиторий проектов."""

from sqlalchemy.orm import Session

from common.singleton_meta import SingletonMeta
from domains.project.project_model import ProjectModel


class ProjectRepository(metaclass=SingletonMeta):

    def find_by_id(self, project_id: int, session: Session) -> ProjectModel | None:
        return session.get(ProjectModel, project_id)

    def save(self, project: ProjectModel, session: Session) -> ProjectModel:
        merged = session.merge(project)
        session.flush()
        return merged
