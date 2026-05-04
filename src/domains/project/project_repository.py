# project_repository.py
"""Репозиторий проектов."""

from sqlalchemy.orm import Session
from domains.project.project_model import ProjectModel

class ProjectRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, project_id: int) -> ProjectModel | None:
        return self._session.get(ProjectModel, project_id)

    def save(self, project: ProjectModel) -> ProjectModel:
        merged = self._session.merge(project)
        self._session.flush()
        return merged
