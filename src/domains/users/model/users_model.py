# users_model.py
"""SQLAlchemy ORM-модель таблицы users."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base


class UsersModel(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index(
            'idx_users_only_one_local',
            'subject_id',
            unique=True,
            postgresql_where=text('is_tech_user = false'),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100))
    is_tech_user: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f'<UsersModel id={self.id} subject_id={self.subject_id!r} email={self.email!r}>'
