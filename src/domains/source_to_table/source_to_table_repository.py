# source_to_table_repository.py
"""Репозиторий маппингов source_to_table."""

from sqlalchemy.orm import Session

from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_model import SourceToTableModel


class SourceToTableRepository(metaclass=SingletonMeta):

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, record_id: int) -> SourceToTableModel | None:
        return self._session.get(SourceToTableModel, record_id)

    def find_by_project_id(self, project_id: int) -> list[SourceToTableModel]:
        return (
            self._session.query(SourceToTableModel)
            .filter(SourceToTableModel.project_id == project_id)
            .all()
        )

    def save(self, record: SourceToTableModel) -> SourceToTableModel:
        merged = self._session.merge(record)
        self._session.flush()
        return merged

