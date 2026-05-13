# data_stream.py
"""Универсальный поток табличных данных для загрузчика.

Любой источник (openpyxl, csv, JSON-стрим и т.д.) оборачивается вызывающей
стороной в DataStream. headers нужны только для MAP_BY_COLUMN_NAME; для
MAP_BY_COLUMN_NUMBER можно передать пустой список.

rows_factory вызывается каждый раз, когда нужен свежий итератор по строкам
файла (отдельно для валидации и для загрузки). Это позволяет проходить файл
несколько раз без полной буферизации в памяти.
"""
from typing import Any, Callable, Iterator, Sequence


class DataStream:

    def __init__(
        self,
        headers: list[str],
        rows_factory: Callable[[], Iterator[Sequence[Any]]],
    ) -> None:
        self.headers = headers
        self._rows_factory = rows_factory

    def iter_rows(self) -> Iterator[Sequence[Any]]:
        return self._rows_factory()
