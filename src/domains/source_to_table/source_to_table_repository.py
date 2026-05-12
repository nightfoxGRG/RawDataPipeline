# source_to_table_repository.py
"""Репозиторий маппингов source_to_table."""

from sqlalchemy import delete
from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel
from domains.source_to_table.source_to_table_model import SourceToTableModel


@repository
class SourceToTableRepository(metaclass=SingletonMeta):

    def find_by_config_id(self, config_id: int) -> list[SourceToTableModel]:
        return (
            self._session.query(SourceToTableModel)
            .filter(SourceToTableModel.source_to_table_config_id == config_id)
            .order_by(SourceToTableModel.source_column_order)
            .all()
        )

    def find_existing_table_names(self, project_id: int, table_names: list[str]) -> list[str]:
        rows = (
            self._session.query(SourceToTableConfigModel.table_name)
            .join(SourceToTableModel, SourceToTableModel.source_to_table_config_id == SourceToTableConfigModel.id)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names),
            )
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def delete_by_config_id(self, config_id: int) -> None:
        self._session.execute(
            delete(SourceToTableModel)
            .where(SourceToTableModel.source_to_table_config_id == config_id)
        )
        self._session.flush()

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str]) -> None:
        if not table_names:
            return
        config_ids = [
            row[0] for row in (
                self._session.query(SourceToTableConfigModel.id)
                .filter(
                    SourceToTableConfigModel.project_id == project_id,
                    SourceToTableConfigModel.table_name.in_(table_names),
                )
                .all()
            )
        ]
        if not config_ids:
            return
        self._session.execute(
            delete(SourceToTableModel)
            .where(SourceToTableModel.source_to_table_config_id.in_(config_ids))
        )
        self._session.flush()

    def save_all(self, entities: list[SourceToTableModel]) -> list[SourceToTableModel]:
        if not entities:
            return []
        self._session.bulk_save_objects(entities, return_defaults=True)
        self._session.flush()
        return entities
