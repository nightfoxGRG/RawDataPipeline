# loader_service.py
"""Универсальный загрузчик данных в таблицу рабочей БД.

Читает конфигурацию маппинга из source_to_table_config / source_to_table,
буферизует входной поток по чанкам, валидирует типы и NOT NULL поля.
Если есть ошибки — возвращает весь список без вставки. Если ошибок нет —
выполняет INSERT блоками chunk_size.
"""
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Callable, Sequence

from common.error import AppError
from common.singleton_meta import SingletonMeta
from domains.loader.data_stream import DataStream
from domains.source_to_table.source_to_table_config_repository import SourceToTableConfigRepository
from domains.source_to_table.source_to_table_repository import SourceToTableRepository
from domains.working_db.information_schema_repository import InformationSchemaRepository
from domains.working_db.working_db_repository import WorkingDbRepository

_MAP_BY_NAME = 'MAP_BY_COLUMN_NAME'
_MAP_BY_NUMBER = 'MAP_BY_COLUMN_NUMBER'

_FN_PACKAGE_ID = 'PACKAGE_ID'
_FN_PACKAGE_TIMESTAMP = 'PACKAGE_TIMESTAMP'
_FN_SOURCE = 'SOURCE'
_FN_SERIAL = 'SERIAL'

_MAX_REPORTED_ERRORS = 50

_INT_TYPES = {'integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8'}
_NUM_TYPES = {'numeric', 'decimal', 'real', 'double precision', 'float', 'float4', 'float8', 'money'}
_BOOL_TYPES = {'boolean', 'bool'}
_DATE_TYPES = {'date'}
_TS_TYPES = {'timestamp', 'timestamp without time zone', 'timestamp with time zone', 'timestamptz'}
_BOOL_TRUE = {'true', 't', '1', 'yes', 'y', 'да'}
_BOOL_FALSE = {'false', 'f', '0', 'no', 'n', 'нет'}

# Formats: '2025-12-08 15:57:00.000 +0300', '2025-12-08T15:57:00+03:00', etc.
_RE_TZ_SPACE = re.compile(r'(\d)\s+([+-]\d{2}:?\d{2})$')
_RE_TZ_NO_COLON = re.compile(r'([+-])(\d{2})(\d{2})$')


def _normalize_dt(s: str) -> str:
    s = _RE_TZ_SPACE.sub(r'\1\2', s)       # убираем пробел перед tz: '00.000 +0300' → '00.000+0300'
    s = s.replace(' ', 'T', 1)              # первый пробел = разделитель даты и времени
    s = _RE_TZ_NO_COLON.sub(r'\1\2:\3', s) # +0300 → +03:00
    return s


class LoaderService(metaclass=SingletonMeta):

    def __init__(self) -> None:
        self._config_repository = SourceToTableConfigRepository()
        self._source_to_table_repository = SourceToTableRepository()
        self._working_db_repository = WorkingDbRepository()
        self._information_schema_repository = InformationSchemaRepository()

    def load(
        self,
        db_id: int,
        schema: str,
        config_id: int,
        source_name: str,
        stream: DataStream,
    ) -> int:
        if not db_id:
            raise AppError('Не указан идентификатор рабочей БД.')
        if not schema:
            raise AppError('Не указана схема.')
        if not config_id:
            raise AppError('Не указан идентификатор конфигурации маппинга.')

        config = self._config_repository.find_by_id(config_id)
        if not config:
            raise AppError('Конфигурация маппинга не найдена.')
        if not config.table_name:
            raise AppError('В конфигурации не указана таблица.')
        if config.map_type not in (_MAP_BY_NAME, _MAP_BY_NUMBER):
            raise AppError(f'Неподдерживаемый тип маппинга: {config.map_type}.')

        target_table = config.table_name
        chunk_size = int(config.chunk_size) if config.chunk_size else 1000
        if chunk_size < 1:
            chunk_size = 1000

        records = self._source_to_table_repository.find_by_config_id(config_id)
        if not records:
            raise AppError('Маппинг не настроен — нет записей в source_to_table.')

        col_meta_rows = self._information_schema_repository.get_columns_metadata(db_id, schema, target_table)
        if not col_meta_rows:
            raise AppError(f'Таблица {target_table} не найдена в схеме {schema}.')
        col_meta = {
            row[0]: {
                'data_type': row[1],
                'is_nullable': (row[2] or '').upper() == 'YES',
                'has_default': row[3] is not None,
            }
            for row in col_meta_rows
        }

        # --- Статические проверки маппинга ---
        # Прогоняем ВСЕ виды проверок и собираем сводный список ошибок.

        mapping_errors = self._check_mapping_has_source(records, config.map_type)
        not_null_errors = self._check_not_null_columns_mapped(records, col_meta, config.map_type)

        header_idx = {h.lower(): i for i, h in enumerate(stream.headers or [])}
        header_errors = self._collect_missing_source_columns(
            records, config.map_type, header_idx, len(stream.headers or [])
        )

        static_errors: list[str] = []
        if mapping_errors:
            static_errors.append('Маппинг:')
            static_errors.extend('  • ' + e for e in mapping_errors)
        if not_null_errors:
            static_errors.append('NOT NULL колонки таблицы:')
            static_errors.extend('  • ' + e for e in not_null_errors)
        if header_errors:
            static_errors.append('Колонки источника в заголовках файла:')
            static_errors.extend('  • ' + e for e in header_errors)

        if static_errors:
            raise AppError('\n'.join(static_errors))

        package_id = str(uuid.uuid4())
        package_timestamp = datetime.now(timezone.utc)

        target_columns, resolvers, target_records = self._build_resolvers(
            records=records,
            map_type=config.map_type,
            header_idx=header_idx,
            source_name=source_name,
            package_id=package_id,
            package_timestamp=package_timestamp,
        )
        if not target_columns:
            raise AppError('Нет целевых колонок для записи.')

        # --- Проход 1: чанковая валидация данных без буферизации файла ---
        # Читаем чанк → валидируем → отбрасываем → следующий чанк.

        errors: list[str] = []
        chunk_buf: list[tuple[int, Sequence[Any]]] = []
        row_idx = 1  # заголовок — строка 1, данные с 2
        for row in stream.iter_rows():
            row_idx += 1
            chunk_buf.append((row_idx, row))
            if len(chunk_buf) >= chunk_size:
                errors.extend(self._validate_chunk(chunk_buf, target_columns, target_records, resolvers, col_meta))
                chunk_buf = []
                if len(errors) >= _MAX_REPORTED_ERRORS:
                    break
        if chunk_buf and len(errors) < _MAX_REPORTED_ERRORS:
            errors.extend(self._validate_chunk(chunk_buf, target_columns, target_records, resolvers, col_meta))

        if errors:
            truncated = errors[:_MAX_REPORTED_ERRORS]
            msg = '\n'.join(truncated)
            if len(errors) > _MAX_REPORTED_ERRORS:
                msg += f'\n… и ещё ошибок: {len(errors) - _MAX_REPORTED_ERRORS}'
            raise AppError(msg)

        # --- Проход 2: чанковая вставка в таблицу без буферизации файла ---
        # Перечитываем файл, набираем чанк → INSERT → отбрасываем → следующий.

        insert_sql = self._build_insert_sql(schema, target_table, target_columns)
        return self._stream_insert(db_id, schema, insert_sql, stream.iter_rows(), resolvers, chunk_size)

    # ── Статические проверки ────────────────────────────────────────────────

    def _check_mapping_has_source(self, records, map_type: str) -> list[str]:
        data_records = [r for r in records if not r.function and r.table_column]
        if map_type == _MAP_BY_NAME:
            if not any((r.source_column or '').strip() for r in data_records):
                return ['В маппинге не заполнен код колонки источника ни для одной колонки данных.']
        elif map_type == _MAP_BY_NUMBER:
            if not any(r.source_column_number is not None for r in data_records):
                return ['В маппинге не заполнен номер колонки источника ни для одной колонки данных.']
        return []

    def _check_not_null_columns_mapped(self, records, col_meta: dict, map_type: str) -> list[str]:
        errors: list[str] = []
        rec_by_col = {r.table_column: r for r in records if r.table_column}
        for col_name, meta in col_meta.items():
            if meta['is_nullable'] or meta['has_default']:
                continue
            rec = rec_by_col.get(col_name)
            if not rec:
                errors.append(f'NOT NULL колонка «{col_name}» отсутствует в маппинге.')
                continue
            if rec.function:
                continue
            if map_type == _MAP_BY_NAME and not (rec.source_column or '').strip():
                errors.append(f'NOT NULL колонка «{col_name}»: не задан код колонки источника.')
            elif map_type == _MAP_BY_NUMBER and rec.source_column_number is None:
                errors.append(f'NOT NULL колонка «{col_name}»: не задан номер колонки источника.')
        return errors

    def _collect_missing_source_columns(self, records, map_type: str, header_idx: dict[str, int], header_count: int) -> list[str]:
        errors: list[str] = []
        for rec in records:
            if rec.function or not rec.table_column:
                continue
            if map_type == _MAP_BY_NAME:
                found = False
                for candidate in (rec.source_column, rec.source_column_description):
                    name = (candidate or '').strip().lower()
                    if name and name in header_idx:
                        found = True
                        break
                if not found:
                    src = (rec.source_column or rec.source_column_description or '').strip()
                    label = f'«{src}» → {rec.table_column}' if src else rec.table_column
                    errors.append(f'Колонка источника не найдена в файле: {label}.')
            elif map_type == _MAP_BY_NUMBER:
                num = rec.source_column_number
                if num is None or num < 1 or num > header_count:
                    errors.append(f'Колонка источника №{num} не найдена в файле (→ {rec.table_column}).')
        return errors

    # ── Чанковая валидация данных ───────────────────────────────────────────

    def _validate_chunk(
        self,
        chunk: list[tuple[int, Sequence[Any]]],
        target_columns: list[str],
        target_records: list,
        resolvers: list[Callable[[Sequence[Any]], Any]],
        col_meta: dict,
    ) -> list[str]:
        errors: list[str] = []
        for row_idx, row in chunk:
            for i, col_name in enumerate(target_columns):
                rec = target_records[i]
                if rec.function:
                    continue
                meta = col_meta.get(col_name)
                if not meta:
                    continue
                value = resolvers[i](row)
                if self._is_null_value(value):
                    if not meta['is_nullable']:
                        errors.append(f'строка {row_idx}, колонка «{col_name}»: значение не может быть NULL.')
                    continue
                type_err = self._validate_type(value, meta['data_type'])
                if type_err:
                    errors.append(f'строка {row_idx}, колонка «{col_name}»: {type_err}')
        return errors

    @staticmethod
    def _is_null_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    @staticmethod
    def _validate_type(value: Any, data_type: str) -> str | None:
        t = (data_type or '').strip().lower()
        if t in _INT_TYPES:
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return None
            if isinstance(value, float):
                if not value.is_integer():
                    return f'ожидается целое число, получено: {value!r}'
                return None
            try:
                int(str(value).strip())
                return None
            except (ValueError, TypeError):
                return f'ожидается целое число, получено: {value!r}'
        if t in _NUM_TYPES:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return None
            try:
                float(str(value).strip().replace(',', '.'))
                return None
            except (ValueError, TypeError):
                return f'ожидается число, получено: {value!r}'
        if t in _BOOL_TYPES:
            if isinstance(value, bool):
                return None
            s = str(value).strip().lower()
            if s in _BOOL_TRUE or s in _BOOL_FALSE:
                return None
            return f'ожидается boolean, получено: {value!r}'
        if t in _DATE_TYPES:
            if isinstance(value, (date, datetime)):
                return None
            try:
                datetime.fromisoformat(_normalize_dt(str(value).strip()))
                return None
            except (ValueError, TypeError):
                return f'ожидается дата, получено: {value!r}'
        if t in _TS_TYPES:
            if isinstance(value, datetime):
                return None
            if isinstance(value, date):
                return None
            try:
                datetime.fromisoformat(_normalize_dt(str(value).strip()))
                return None
            except (ValueError, TypeError):
                return f'ожидается timestamp, получено: {value!r}'
        # строковые / прочие типы — принимаем как есть
        return None

    # ── Построение resolver-ов и INSERT-а ───────────────────────────────────

    def _stream_insert(
        self,
        db_id: int,
        schema: str,
        insert_sql: str,
        rows: Sequence[Sequence[Any]],
        resolvers: list[Callable[[Sequence[Any]], Any]],
        chunk_size: int,
    ) -> int:
        total = 0
        batch: list[dict] = []
        for row in rows:
            batch.append({
                f'p{i}': (None if self._is_null_value(v := resolver(row)) else v)
                for i, resolver in enumerate(resolvers)
            })
            if len(batch) >= chunk_size:
                self._working_db_repository.execute_insert_batch(db_id, schema, insert_sql, batch)
                total += len(batch)
                batch = []
        if batch:
            self._working_db_repository.execute_insert_batch(db_id, schema, insert_sql, batch)
            total += len(batch)
        return total

    def _build_resolvers(
        self,
        records,
        map_type: str,
        header_idx: dict[str, int],
        source_name: str,
        package_id: str,
        package_timestamp: datetime,
    ) -> tuple[list[str], list[Callable[[Sequence[Any]], Any]], list]:
        target_columns: list[str] = []
        resolvers: list[Callable[[Sequence[Any]], Any]] = []
        target_records: list = []

        for rec in records:
            if not rec.table_column:
                continue
            if rec.function == _FN_SERIAL:
                continue

            target_columns.append(rec.table_column)
            target_records.append(rec)

            if rec.function == _FN_PACKAGE_ID:
                resolvers.append(lambda _row, v=package_id: v)
            elif rec.function == _FN_PACKAGE_TIMESTAMP:
                resolvers.append(lambda _row, v=package_timestamp: v)
            elif rec.function == _FN_SOURCE:
                resolvers.append(lambda _row, v=source_name: v)
            else:
                resolvers.append(self._mapping_resolver(rec, map_type, header_idx))

        return target_columns, resolvers, target_records

    def _mapping_resolver(self, rec, map_type: str, header_idx: dict[str, int]) -> Callable[[Sequence[Any]], Any]:
        if map_type == _MAP_BY_NAME:
            for candidate in (rec.source_column, rec.source_column_description):
                name = (candidate or '').strip().lower()
                if name and name in header_idx:
                    idx = header_idx[name]
                    return lambda row, i=idx: row[i] if i < len(row) else None
            return lambda _row: None
        # MAP_BY_COLUMN_NUMBER — 1-based в БД, превращаем в 0-based
        num = rec.source_column_number
        if num is None or num < 1:
            return lambda _row: None
        idx = num - 1
        return lambda row, i=idx: row[i] if 0 <= i < len(row) else None

    def _build_insert_sql(self, schema: str, table: str, columns: list[str]) -> str:
        cols_sql = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join(f':p{i}' for i in range(len(columns)))
        return f'INSERT INTO "{schema}"."{table}" ({cols_sql}) VALUES ({placeholders})'
