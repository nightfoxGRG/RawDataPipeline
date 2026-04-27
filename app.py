import sys
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from src.domains.sql_generator.sql_generator_service import generate_sql_from_config
from src.domains.table_config.table_config_generator_service import generate_excel_config_v2
from src.config.config_loader import load_config
from src.config.db_migration_yoyo.db_migrate_config_at_start import run_migrations_on_start
from src.inferrer import ALLOWED_DATA_EXTENSIONS, infer_columns, read_data_file
from src.common.error import AppError

_CONFIG_PATH = Path(__file__).parent / 'config' / 'config.toml'


def _load_config() -> dict:
    try:
        return load_config()
    except Exception:
        return {}


def create_app() -> Flask:
    app = Flask(__name__)

    _cfg = _load_config()
    # Определяем режим запуска: локальный (PyInstaller .exe/.app) или серверный
    _run_mode = 'local' if getattr(sys, 'frozen', False) else 'server'
    _project_name = _cfg.get('app', {}).get('project_name', 'DataPipelinePro')

    # Автоматически применить миграции БД при старте
    run_migrations_on_start()

    @app.context_processor
    def inject_globals():
        return {'run_mode': _run_mode, 'project_name': _project_name}

    @app.route('/', methods=['GET'])
    def index():
        return render_template('inferrer.html', errors=[])

    @app.get('/sql_generator_from_config')
    def get_sql_generator_from_config():
        return render_template(
            'index.html',
            sql_output='',
            errors=[],
            add_pk=True,
            add_package_fields=True,
        )

    @app.post('/sql_generator_from_config')
    def post_sql_generator_from_config():
        sql_output, errors, add_pk, add_package_fields = generate_sql_from_config(
            request.files, request.form
        )
        return render_template(
            'index.html',
            sql_output=sql_output,
            errors=errors,
            add_pk=add_pk,
            add_package_fields=add_package_fields,
        )

    @app.get('/inferrer')
    def inferrer():
        return render_template('inferrer.html', errors=[])

    @app.post('/inferrer/generate')
    def inferrer_generate():
        file_storage = request.files.get('data_file')
        if file_storage is None or not file_storage.filename:
            return jsonify(error='Не выбран файл данных.'), 400

        filename = file_storage.filename
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_DATA_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_DATA_EXTENSIONS))
            return jsonify(error=f'Поддерживаются только файлы: {allowed}'), 400

        content = file_storage.read()
        if not content:
            return jsonify(error='Загруженный файл пустой.'), 400

        add_pk = request.form.get('add_pk') == '1'
        add_package_fields = request.form.get('add_package_fields') == '1'

        try:
            table_name, headers, rows = read_data_file(content, filename)
            columns = infer_columns(headers, rows)
            xlsx_bytes = generate_excel_config_v2(table_name, columns, add_pk=add_pk, add_package_fields=add_package_fields)
        except (AppError, Exception) as exc:
            return jsonify(error=str(exc)), 422

        download_name = f'{table_name}_config.xlsm'
        ascii_name = download_name.encode('ascii', 'replace').decode('ascii')
        encoded_name = quote(download_name, encoding='utf-8')
        return Response(
            xlsx_bytes,
            mimetype='application/vnd.ms-excel.sheet.macroEnabled.12',
            headers={
                'Content-Disposition': (
                    f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}"
                ),
            },
        )

    @app.get('/download-template')
    def download_template():
        static_dir = Path(app.root_path) / 'static'
        return send_from_directory(
            static_dir,
            'TablesConfig.xlsm',
            as_attachment=True,
            download_name='TablesConfig.xlsm',
        )

    @app.post('/download')
    def download_sql():
        sql_content = request.form.get('sql_output', '').strip()
        if not sql_content:
            return render_template('index.html', errors=['SQL для скачивания не найден.'])

        return Response(
            sql_content,
            mimetype='application/sql',
            headers={'Content-Disposition': 'attachment; filename=tables.sql'},
        )

    return app


app = create_app()


if __name__ == '__main__':
    app.run(port=8080)
