# user_setting_model.py
"""SQLAlchemy ORM-модель таблицы user_setting."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base


class UserSettingModel(Base):
    __tablename__ = 'user_setting'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), unique=True, nullable=False)
    actual_project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('project.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<UserSettingModel id={self.id} user_id={self.user_id} actual_project_id={self.actual_project_id}>'
