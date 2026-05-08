# source_to_table_repository.py
"""Репозиторий маппингов source_to_table."""

from sqlalchemy import delete
from common.db_decorator.repository_decorator import repository
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_model import SourceToTableModel


@repository
class SourceToTableRepository(metaclass=SingletonMeta):

    def find_by_project_and_table(self, project_id: int, table_name: str) -> list[SourceToTableModel]:
        return (
            self._session.query(SourceToTableModel)
            .filter(
                SourceToTableModel.project_id == project_id,
                SourceToTableModel.table_name == table_name,
            )
            .order_by(SourceToTableModel.source_column_order)
            .all()
        )

    def find_existing_table_names(self, project_id: int, table_names: list[str]) -> list[str]:
        return [
            row[0] for row in (
                self._session.query(SourceToTableModel.table_name)
                .filter(
                    SourceToTableModel.project_id == project_id,
                    SourceToTableModel.table_name.in_(table_names),
                )
                .distinct()
                .all()
            )
        ]

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str]) -> None:
        if not table_names:
            return  # Ничего не удаляем, если список пуст

        self._session.execute(
            delete(SourceToTableModel)
            .where(
                SourceToTableModel.project_id == project_id,
                SourceToTableModel.table_name.in_(table_names)
            )
        )
        self._session.flush()


    def save(self, entity: SourceToTableModel) -> SourceToTableModel:
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def save_all(self, entities: list[SourceToTableModel]) -> list[SourceToTableModel]:
        if not entities:
            return []

        # bulk_save_objects автоматически обрабатывает вставку/обновление
        self._session.bulk_save_objects(entities, return_defaults=True)
        self._session.flush()
        return entities