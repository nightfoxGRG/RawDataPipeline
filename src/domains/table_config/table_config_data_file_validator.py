# table_config_data_file_validator.py
from common.singleton_meta import SingletonMeta
from common.error import ValidationError


class TableConfigDataFileValidator(metaclass=SingletonMeta):

    def validate_data_file(self, headers: list[str], rows: list[list]) -> None:
        errors: list[str] = []

        if not headers:
            errors.append('Файл не содержит ни одной колонки.')
            raise ValidationError(errors=errors)

        for i, header in enumerate(headers, start=1):
            if not header or not str(header).strip():
                errors.append(f'Колонка {i}: заголовок не может быть пустым.')

        seen: dict[str, int] = {}
        for i, header in enumerate(headers, start=1):
            key = str(header).strip().lower()
            if key in seen:
                errors.append(f'Колонка {i}: дублирует заголовок колонки {seen[key]} ("{header}").')
            else:
                seen[key] = i

        if not rows:
            errors.append('Файл не содержит строк с данными — невозможно определить типы колонок.')

        if errors:
            raise ValidationError(errors=errors)

    def validate_translated_columns(self, columns: list[dict]) -> None:
        errors: list[str] = []
        seen: dict[str, str] = {}
        for col in columns:
            code = col['code']
            label = col.get('label') or code
            if code in seen:
                errors.append(
                    f'Колонка "{label}": после перевода получает код "{code}", '
                    f'который уже занят колонкой "{seen[code]}".'
                )
            else:
                seen[code] = label

        if errors:
            raise ValidationError(errors=errors)
