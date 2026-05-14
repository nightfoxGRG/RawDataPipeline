# db_setting_credential_model.py
"""SQLAlchemy ORM-модель таблицы db_setting_credential."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from config.db_orm_sqlalchemy.db_base_config import Base


class DbSettingCredentialModel(Base):
    __tablename__ = 'db_setting_credential'
    __table_args__ = (
        UniqueConstraint('user_id', 'db_setting_id', name='unique_user_db_setting_credential'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    db_setting_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('db_setting.id'), nullable=False)
    login: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<DbSettingCredentialModel id={self.id} user_id={self.user_id} db_setting_id={self.db_setting_id}>'
