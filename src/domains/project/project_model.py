# project_model.py
"""SQLAlchemy ORM-модель таблицы project."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base
import domains.users.model.users_model  # noqa: F401 — регистрирует таблицу users в метаданных


class ProjectModel(Base):
    __tablename__ = 'project'
    __table_args__ = (
        UniqueConstraint('schema', name='project_schema_unique'),
        CheckConstraint(
            "schema NOT IN ('public', 'pg_catalog', 'information_schema', 'pg_toast', 'data_pipline_schema')",
            name='project_schema_forbidden',
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schema: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'))
    table_config_minio_id: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f'<ProjectModel id={self.id} schema={self.schema!r}>'
