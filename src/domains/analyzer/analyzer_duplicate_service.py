# analyzer_duplicate_service.py
"""Поиск подобных дубликатов в колонках таблицы.

Подобные дубликаты — значения, которые после нормализации совпадают,
но в исходном виде различаются. Паттерны нормализации:
  • регистр:         "Example" == "example" == "exAMple"
  • пробелы вокруг:  "  value  " == "value"
  • множественные пробелы: "ex  ample" == "ex ample"
  • дефис/нижнее подчёркивание как пробел: "ex-ample" == "ex_ample" == "ex ample"
  • буква ё↔е (для русского текста): "ёж" == "еж"
"""
import re
from collections import defaultdict
from typing import Any, Sequence

from common.singleton_meta import SingletonMeta

_RE_NOISE = re.compile(r'[\s\-_]+')

# Латинские буквы, визуально неотличимые от кириллических → заменяем на кириллические
_LATIN_TO_CYR = str.maketrans({
    'A': 'А', 'a': 'а',
    'B': 'В',
    'C': 'С', 'c': 'с',
    'E': 'Е', 'e': 'е',
    'H': 'Н',
    'K': 'К',
    'M': 'М',
    'O': 'О', 'o': 'о',
    'P': 'Р', 'p': 'р',
    'T': 'Т',
    'X': 'Х', 'x': 'х',
    'y': 'у', 'Y': 'У',
})


def _normalize(value: str) -> str:
    v = value.strip()
    v = v.translate(_LATIN_TO_CYR)
    v = v.lower()
    v = v.replace('ё', 'е')
    v = _RE_NOISE.sub('', v)
    return v


class AnalyzerDuplicateService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        # buf[table][col] -> norm_key -> set of original values
        self._buf: dict[str, dict[str, dict[str, set[str]]]] = {}

    def reset(self) -> None:
        self._buf.clear()

    def process_chunk(
        self,
        table: str,
        columns: list[str],
        chunk: Sequence[Sequence[Any]],
    ) -> None:
        if table not in self._buf:
            self._buf[table] = {}
        tbl = self._buf[table]
        for col in columns:
            if col not in tbl:
                tbl[col] = defaultdict(set)

        col_idx = {col: i for i, col in enumerate(columns)}
        for row in chunk:
            for col in columns:
                raw = row[col_idx[col]]
                if raw is None:
                    continue
                s = str(raw)
                if not s.strip():
                    continue
                norm = _normalize(s)
                tbl[col][norm].add(s)

    def get_duplicates(self, table: str) -> dict[str, list[list[str]]]:
        """Возвращает {col: [[v1, v2, ...], ...]} — только группы с ≥2 уникальных исходных значений."""
        result: dict[str, list[list[str]]] = {}
        tbl = self._buf.get(table, {})
        for col, norm_map in tbl.items():
            groups = [
                sorted(originals)
                for originals in norm_map.values()
                if len(originals) >= 2
            ]
            if groups:
                result[col] = groups
        return result
