# source_to_table_config_repository.py
"""Репозиторий конфигураций маппинга source_to_table_config."""

from sqlalchemy.orm import Session

from common.db_error_handler import handle_db_errors
from common.singleton_meta import SingletonMeta
from domains.source_to_table.source_to_table_config_model import SourceToTableConfigModel


@handle_db_errors
class SourceToTableConfigRepository(metaclass=SingletonMeta):

    def find_existing_table_names(self, project_id: int, table_names: list[str], session: Session) -> set[str]:
        rows = (
            session.query(SourceToTableConfigModel.table_name)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name.in_(table_names),
            )
            .all()
        )
        return {row[0] for row in rows}

    def upsert_map_type(self, project_id: int, table_name: str, map_type: str, session: Session) -> None:
        record = (
            session.query(SourceToTableConfigModel)
            .filter(
                SourceToTableConfigModel.project_id == project_id,
                SourceToTableConfigModel.table_name == table_name,
            )
            .first()
        )
        if record:
            record.map_type = map_type
        else:
            session.add(SourceToTableConfigModel(
                project_id=project_id,
                table_name=table_name,
                map_type=map_type,
            ))

    def delete_by_project_and_table(self, project_id: int, table_name: str, session: Session) -> None:
        session.query(SourceToTableConfigModel).filter(
            SourceToTableConfigModel.project_id == project_id,
            SourceToTableConfigModel.table_name == table_name,
        ).delete(synchronize_session=False)

    def delete_by_project_and_tables(self, project_id: int, table_names: list[str], session: Session) -> None:
        session.query(SourceToTableConfigModel).filter(
            SourceToTableConfigModel.project_id == project_id,
            SourceToTableConfigModel.table_name.in_(table_names),
        ).delete(synchronize_session=False)
