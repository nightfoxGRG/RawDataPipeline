# db_error_handler.py
import functools
import inspect

from sqlalchemy.exc import SQLAlchemyError
from common.error import AppError


def _wrap(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except SQLAlchemyError as e:
            orig = getattr(e, 'orig', None)
            raise AppError(str(orig).strip() if orig else str(e).strip()) from e
    return wrapper


def handle_db_errors(cls):
    for name, obj in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_'):
            setattr(cls, name, _wrap(obj))
    return cls
