# file_util.py
from pathlib import Path

from werkzeug.datastructures import FileStorage

from common.error import UploadError

def read_uploaded_file(file_storage: FileStorage | None, allowed_extensions: set[str]) -> tuple[bytes, str]:
    if file_storage is None or not file_storage.filename:
        raise UploadError('Не выбран файл конфигурации.')

    filename = file_storage.filename
    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        allowed = ', '.join(sorted(allowed_extensions))
        raise UploadError(f'Поддерживаются только файлы: {allowed}')

    content = file_storage.read()
    if not content:
        raise UploadError('Загруженный файл пустой.')

    return content, filename
