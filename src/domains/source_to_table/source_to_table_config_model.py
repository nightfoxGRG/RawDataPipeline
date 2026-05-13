# source_to_table_config_model.py
"""SQLAlchemy ORM-модель таблицы source_to_table_config."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base

class SourceToTableConfigModel(Base):
    __tablename__ = 'source_to_table_config'
    __table_args__ = (
        Index('idx_source_to_table_config_unique', 'project_id', 'table_name', 'code', unique=True),
        CheckConstraint(
            "map_type IN ('MAP_BY_COLUMN_NAME', 'MAP_BY_COLUMN_NUMBER')",
            name='allowed_map_type',
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('project.id'), nullable=False)
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<SourceToTableConfigModel id={self.id} table={self.table_name!r} map_type={self.map_type!r} chunk_size={self.chunk_size!r}>'