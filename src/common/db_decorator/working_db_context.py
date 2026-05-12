# working_db_context.py
from contextvars import ContextVar
from typing import Optional, List
from sqlalchemy.orm import Session
from common.singleton_meta import SingletonMeta


class WorkingDbContext(metaclass=SingletonMeta):
    """Контекст для хранения текущей сессии БД с использованием ContextVar."""

    # Стек сессий для поддержки вложенных транзакций
    _session_stack: ContextVar[List[Session]] = ContextVar('working_db_session_stack', default=[])

    def push_session(cls, session: Session) -> None:
        """Помещает сессию в стек контекста."""
        stack = cls._session_stack.get()
        stack.append(session)
        cls._session_stack.set(stack)

    def pop_session(cls) -> Optional[Session]:
        """Извлекает сессию из стека контекста."""
        stack = cls._session_stack.get()
        if stack:
            session = stack.pop()
            cls._session_stack.set(stack)
            return session
        return None

    def get_current_session(cls) -> Optional[Session]:
        """Возвращает текущую активную сессию."""
        stack = cls._session_stack.get()
        return stack[-1] if stack else None

    def clear(cls) -> None:
        """Очищает стек сессий для текущего контекста."""
        cls._session_stack.set([])

    def is_active(cls) -> bool:
        """Проверяет, есть ли активная сессия."""
        return cls.get_current_session() is not None