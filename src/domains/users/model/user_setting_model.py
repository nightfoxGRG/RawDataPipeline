# user_setting_model.py
"""SQLAlchemy ORM-модель таблицы user_setting."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base


class UserSettingModel(Base):
    __tablename__ = 'user_setting'

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), primary_key=True)
    actual_project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('project.id'))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'))

    def __repr__(self) -> str:
        return (
            f'<UserSettingModel user_id={self.user_id}'
            f' actual_project_id={self.actual_project_id}'
            f' actual_db_setting_id={self.actual_db_setting_id}>'
        )
