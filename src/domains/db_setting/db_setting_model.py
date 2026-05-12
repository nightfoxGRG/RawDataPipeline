# db_setting_model.py
"""SQLAlchemy ORM-модель таблицы db_setting."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base


class DbSettingModel(Base):
    __tablename__ = 'db_setting'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    db_label: Mapped[str] = mapped_column(String(100), nullable=False)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    db_user: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'))

    def __repr__(self) -> str:
        return f'<DbSettingModel id={self.id} db_label={self.db_label!r} host={self.host!r}>'