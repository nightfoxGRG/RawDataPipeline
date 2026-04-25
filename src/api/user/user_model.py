"""SQLAlchemy ORM-модели."""

from datetime import datetime

from sqlalchemy import Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.sqlalchemy_db_orm.db_base_config import Base


class User(Base):
    """Пользователь системы.

    Таблица: "user" (имя в кавычках, т.к. user — зарезервированное слово PostgreSQL).
    """

    __tablename__ = 'user'
    # Имя таблицы — зарезервированное слово, нужно цитировать
    __table_args__ = {'quote': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    subject_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment='Внешний идентификатор пользователя (например, из Keycloak)',
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment='Отображаемое имя пользователя',
    )

    email: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='Электронная почта',
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        comment='Дата и время создания записи',
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment='Дата и время последнего обновления',
    )

    def __repr__(self) -> str:
        return f'<User id={self.id} name={self.name!r} email={self.email!r}>'

