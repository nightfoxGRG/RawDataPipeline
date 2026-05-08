# source_to_table_config_repository.py
"""Репозиторий конфигураций маппинга source_to_table_config."""

from sqlalchemy import delete
from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel


@repository
class SourceToTableConfigRepository(metaclass=SingletonMeta):

    def find_existing_table_names(self, project_id: int, table_names: list[str]) -> set[str]:
        rows = (
            self._session.query(SourceToTableConfigModel.table_name)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names),
            )
            .all()
        )
        return {row[0] for row in rows}

    def upsert_map_type(self, project_id: int, table_name: str, map_type: str) -> None:
        record = (
            self._session.query(SourceToTableConfigModel)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name == table_name,
            )
            .first()
        )
        if record:
            record.map_type = map_type
        else:
            self._session.add(SourceToTableConfigModel(
                project_id=project_id,
                table_name=table_name,
                map_type=map_type,
            ))

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str]) -> None:
        if not table_names:
            return  # Ничего не удаляем, если список пуст

        self._session.execute(
            delete(SourceToTableConfigModel)
            .where(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names)
            )
        )
        self._session.flush()

    def save(self, entity: SourceToTableConfigModel) -> SourceToTableConfigModel:
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def save_all(self, entities: list[SourceToTableConfigModel]) -> list[SourceToTableConfigModel]:
        if not entities:
            return []

        # bulk_save_objects автоматически обрабатывает вставку/обновление
        self._session.bulk_save_objects(entities, return_defaults=True)
        self._session.flush()
        return entities