from werkzeug.datastructures import FileStorage


class UploadError(ValueError):
    """Raised when uploaded file is invalid."""


ALLOWED_EXTENSIONS = {'.xlsx', '.xlsm', '.json'}


def read_uploaded_file(file_storage: FileStorage | None) -> tuple[bytes, str]:
    if file_storage is None or not file_storage.filename:
        raise UploadError('Не выбран файл конфигурации.')

    filename = file_storage.filename
    dot_position = filename.rfind('.')
    extension = filename[dot_position:].lower() if dot_position != -1 else ''
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
        raise UploadError(f'Поддерживаются только файлы: {allowed}')

    content = file_storage.read()
    if not content:
        raise UploadError('Загруженный файл пустой.')

    return content, filename
