# source_to_table_model.py
"""SQLAlchemy ORM-модель таблицы source_to_table."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base
import domains.users.model.users_model          # noqa: F401
import domains.source_to_table.source_to_table_config_model  # noqa: F401


class SourceToTableModel(Base):
    __tablename__ = 'source_to_table'
    __table_args__ = (
        Index(
            'idx_source_to_table_table_column_unique',
            'source_to_table_config_id', 'table_column',
            unique=True,
            postgresql_where=text('table_column IS NOT NULL'),
        ),
        CheckConstraint(
            "function IN ('SERIAL', 'PACKAGE_TIMESTAMP', 'PACKAGE_ID', 'SOURCE') OR function IS NULL",
            name='allowed_functions',
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_to_table_config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey('source_to_table_config.id'), nullable=False,
    )
    source_column: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_column_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_column_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_column_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    table_column: Mapped[str | None] = mapped_column(String(200), nullable=True)
    function: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<SourceToTableModel id={self.id} config={self.source_to_table_config_id} table_col={self.table_column!r}>'
