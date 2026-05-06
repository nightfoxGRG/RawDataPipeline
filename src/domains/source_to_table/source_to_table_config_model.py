# source_to_table_config_model.py
"""SQLAlchemy ORM-модель таблицы source_to_table_config."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base
import domains.project.project_model  # noqa: F401


class SourceToTableConfigModel(Base):
    __tablename__ = 'source_to_table_config'
    __table_args__ = (
        Index('idx_source_to_table_config_unique', 'project_id', 'table_name', unique=True),
        CheckConstraint(
            "map_type IN ('MAP_BY_COLUMN_NAME', 'MAP_BY_COLUMN_NUMBER')",
            name='allowed_map_type',
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('project.id'), nullable=False)
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    map_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f'<SourceToTableConfigModel id={self.id} table={self.table_name!r} map_type={self.map_type!r}>'
