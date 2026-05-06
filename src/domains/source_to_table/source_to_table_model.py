# source_to_table_model.py
"""SQLAlchemy ORM-модель таблицы source_to_table."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base
import domains.users.model.users_model  # noqa: F401
import domains.project.project_model     # noqa: F401


class SourceToTableModel(Base):
    __tablename__ = 'source_to_table'
    __table_args__ = (
        Index('idx_source_to_table_table_column_unique', 'project_id', 'table_name', 'table_column', unique=True),
        CheckConstraint(
            "function IN ('SERIAL', 'PACKAGE_TIMESTAMP', 'PACKAGE_ID') OR function IS NULL",
            name='allowed_functions',
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('project.id'), nullable=False)
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_column: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_column_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_column_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_column_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    table_column: Mapped[str] = mapped_column(String(200), nullable=False)
    function: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<SourceToTableModel id={self.id} table={self.table_name!r} source={self.source_column!r}>'
