#app.py
import sys

from flask import Flask, Response, render_template, request, send_from_directory
from common.error import AppError
from common.error_handler import register_error_handlers
from common.project_paths import ProjectPaths
from domains.libretranslate.libretranslate_service import LibreTranslateService
from domains.sql_generator.sql_generator_service import SqlGeneratorService
from domains.sql_generator.sql_generator_validator import SqlGeneratorValidator
from domains.table_config.table_config_data_file_reader_service import TableConfigDataFileReaderService
from domains.table_config.table_config_generator_service import TableConfigGeneratorService
from domains.table_config.table_config_parser_service import TableConfigParserService
from config.config_loader import get_config
from config.db_migration_yoyo.db_migrate_config_at_start import run_migrations_on_start

_SYSTEM_SCHEMA = 'system'

_libretranslate = LibreTranslateService()
_validator = SqlGeneratorValidator()
_reader = TableConfigDataFileReaderService(libretranslate=_libretranslate)
_parser = TableConfigParserService(validator=_validator)
_sql_generator = SqlGeneratorService(parser=_parser, validator=_validator)
_table_config_generator = TableConfigGeneratorService(reader=_reader)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ProjectPaths.TEMPLATES),  # папка с шаблонами
        static_folder=str(ProjectPaths.STATIC)  # папка со статикой (если есть)
    )

    cfg = get_config()
    # Определяем режим запуска: локальный (PyInstaller .exe/.app) или серверный
    _run_mode = 'local' if getattr(sys, 'frozen', False) else 'server'
    _project_name = cfg.get('app', {}).get('project_name', 'DataPipelinePro')

    import os
    if not os.environ.get('FLASK_TESTING'):
        run_migrations_on_start()

    register_error_handlers(app)

    @app.context_processor
    def inject_globals():
        return {'run_mode': _run_mode, 'project_name': _project_name}

    @app.route('/', methods=['GET'])
    def index():
        return render_template('configurator.html')

    @app.get('/generator')
    def get_generator():
        return render_template(
            'generator.html',
            sql_output='',
            add_pk=True,
            add_package_fields=True,
        )

    @app.post('/sql_generator')
    def post_sql_generator():
        sql_output, add_pk, add_package_fields = _sql_generator.generate_sql_from_config(
            request.files, request.form
        )
        return render_template(
            'generator.html',
            sql_output=sql_output,
            add_pk=add_pk,
            add_package_fields=add_package_fields,
        )

    @app.get('/configurator')
    def get_configurator():
        return render_template('configurator.html')

    @app.post('/table_config_generator')
    def post_table_config_generator():
        return _table_config_generator.generate_table_config_from_data_file(request)

    @app.get('/download_table_config_template')
    def download_table_config_template():
        return send_from_directory(
            ProjectPaths.STATIC,
            'TablesConfig.xlsm',
            as_attachment=True,
            download_name='TablesConfig.xlsm',
        )

    @app.post('/download_sql')
    def download_sql():
        sql_content = request.form.get('sql_output', '').strip()
        if not sql_content:
            raise AppError('SQL для скачивания не найден.')

        return Response(
            sql_content,
            mimetype='application/sql',
            headers={'Content-Disposition': 'attachment; filename=tables.sql'},
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True, use_reloader=False)
