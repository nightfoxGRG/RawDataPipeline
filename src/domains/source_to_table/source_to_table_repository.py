# source_to_table_repository.py
"""Репозиторий маппингов source_to_table."""

from sqlalchemy.orm import Session

from common.db_error_handler import handle_db_errors
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_model import SourceToTableModel


@handle_db_errors
class SourceToTableRepository(metaclass=SingletonMeta):

    def find_by_id(self, record_id: int, session: Session) -> SourceToTableModel | None:
        return session.get(SourceToTableModel, record_id)

    def find_by_project_id(self, project_id: int, session: Session) -> list[SourceToTableModel]:
        return (
            session.query(SourceToTableModel)
            .filter(SourceToTableModel.project_id == project_id)
            .all()
        )

    def find_by_project_and_table(self, project_id: int, table_name: str, session: Session) -> list[SourceToTableModel]:
        return (
            session.query(SourceToTableModel)
            .filter(
                SourceToTableModel.project_id == project_id,
                SourceToTableModel.table_name == table_name,
            )
            .order_by(SourceToTableModel.source_column_order)
            .all()
        )

    def find_existing_table_names(self, project_id: int, table_names: list[str], session: Session) -> list[str]:
        return [
            row[0] for row in (
                session.query(SourceToTableModel.table_name)
                .filter(
                    SourceToTableModel.project_id == project_id,
                    SourceToTableModel.table_name.in_(table_names),
                )
                .distinct()
                .all()
            )
        ]

    def delete_by_project_and_table(self, project_id: int, table_name: str, session: Session) -> None:
        session.query(SourceToTableModel).filter(
            SourceToTableModel.project_id == project_id,
            SourceToTableModel.table_name == table_name,
        ).delete(synchronize_session=False)

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str], session: Session) -> None:
        session.query(SourceToTableModel).filter(
            SourceToTableModel.project_id == project_id,
            SourceToTableModel.table_name.in_(table_names),
        ).delete(synchronize_session=False)

    def save(self, record: SourceToTableModel, session: Session) -> SourceToTableModel:
        merged = session.merge(record)
        session.flush()
        return merged

    def delete(self, record: SourceToTableModel, session: Session) -> None:
        session.delete(record)
        session.flush()
