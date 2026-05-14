# project_service.py
"""Сервис проектов."""

from datetime import datetime, timezone

from flask import Response, jsonify

from common.context_service import ContextService
from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.project.project_model import ProjectModel
from domains.project.project_repository import ProjectRepository


def _project_to_dict(p: ProjectModel) -> dict:
    return {
        'id': p.id,
        'code': p.code,
        'description': p.description,
        'db_setting_id': p.db_setting_id,
        'schema': p.schema,
    }


class ProjectService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._repository = ProjectRepository()

    def list_projects(self) -> Response:
        projects = self._repository.find_all()
        return jsonify(projects=[_project_to_dict(p) for p in projects])

    def save_project(self, data: dict) -> Response:
        user = ContextService.get_user_info()
        project_id = data.get('id')
        code = (data.get('code') or '').strip()
        description = (data.get('description') or '').strip()
        db_setting_id = data.get('db_setting_id')
        schema = (data.get('schema') or '').strip()

        if not code:
            raise AppError('Не указан код проекта.')
        if not description:
            raise AppError('Не указано описание проекта.')
        if not db_setting_id:
            raise AppError('Не выбрано подключение к БД.')
        if not schema:
            raise AppError('Не указана схема.')

        if project_id:
            project = self._repository.find_by_id(int(project_id))
            if not project:
                raise AppError('Проект не найден.')
            project.updated_at = datetime.now(timezone.utc)
            project.updated_by = user.user_id
        else:
            project = ProjectModel()
            project.created_by = user.user_id

        project.code = code
        project.description = description
        project.db_setting_id = int(db_setting_id)
        project.schema = schema

        saved = self._repository.save(project)
        return jsonify(project=_project_to_dict(saved))

    def delete_project(self, project_id: int) -> Response:
        project = self._repository.find_by_id(project_id)
        if not project:
            raise AppError('Проект не найден.')
        self._repository.delete(project_id)
        return jsonify(ok=True)
