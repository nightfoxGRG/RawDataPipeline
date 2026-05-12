# source_to_table_config_repository.py
"""Репозиторий конфигураций маппинга source_to_table_config."""

from sqlalchemy import delete
from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel


@repository
class SourceToTableConfigRepository(metaclass=SingletonMeta):

    def find_by_id_and_project(self, config_id: int, project_id: int) -> SourceToTableConfigModel | None:
        record = self._session.get(SourceToTableConfigModel, config_id)
        if record and record.project_id == project_id:
            return record
        return None

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

    def find_all_by_project_and_tables(self, project_id: int, table_names: list[str]) -> list[SourceToTableConfigModel]:
        return (
            self._session.query(SourceToTableConfigModel)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names),
            )
            .all()
        )

    def update_code_description(self, config_id: int, project_id: int, code: str, description: str | None) -> bool:
        record = self._session.get(SourceToTableConfigModel, config_id)
        if not record or record.project_id != project_id:
            return False
        record.code = code
        record.description = description
        self._session.flush()
        return True

    def find_by_project_and_table(self, project_id: int, table_name: str) -> list[SourceToTableConfigModel]:
        return (
            self._session.query(SourceToTableConfigModel)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name == table_name,
            )
            .order_by(SourceToTableConfigModel.code)
            .all()
        )

    def upsert_by_code(self, project_id: int, table_name: str, map_type: str, code: str, created_by: int) -> SourceToTableConfigModel:
        record = (
            self._session.query(SourceToTableConfigModel)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name == table_name,
                SourceToTableConfigModel.code == code,
            )
            .first()
        )
        if record:
            record.map_type = map_type
        else:
            record = SourceToTableConfigModel(
                project_id=project_id,
                table_name=table_name,
                code=code,
                map_type=map_type,
                created_by=created_by,
            )
            self._session.add(record)
        self._session.flush()
        return record

    def set_map_type_and_chunk_size(self, config_id: int, map_type: str, chunk_size: int) -> None:
        record = self._session.get(SourceToTableConfigModel, config_id)
        if record:
            record.map_type = map_type
            record.chunk_size = chunk_size
            self._session.flush()

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str]) -> None:
        if not table_names:
            return
        self._session.execute(
            delete(SourceToTableConfigModel)
            .where(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names),
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
        self._session.bulk_save_objects(entities, return_defaults=True)
        self._session.flush()
        return entities
