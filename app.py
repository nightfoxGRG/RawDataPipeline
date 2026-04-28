import sys

from flask import Flask, Response, render_template, request, send_from_directory
from common.project_paths import ProjectPaths
from domains.sql_generator.sql_generator_service import generate_sql_from_config
from domains.table_config.table_config_generator_service import generate_table_config_from_data_file
from config.config_loader import load_config
from config.db_migration_yoyo.db_migrate_config_at_start import run_migrations_on_start

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ProjectPaths.TEMPLATES),  # папка с шаблонами
        static_folder=str(ProjectPaths.STATIC)  # папка со статикой (если есть)
    )

    cfg = load_config()
    # Определяем режим запуска: локальный (PyInstaller .exe/.app) или серверный
    _run_mode = 'local' if getattr(sys, 'frozen', False) else 'server'
    _project_name = cfg.get('app', {}).get('project_name', 'DataPipelinePro')

    # Автоматически применить миграции БД при старте
    run_migrations_on_start(cfg)

    @app.context_processor
    def inject_globals():
        return {'run_mode': _run_mode, 'project_name': _project_name}

    @app.route('/', methods=['GET'])
    def index():
        return render_template('table_config_generator.html', errors=[])

    @app.get('/sql_generator')
    def get_sql_generator():
        return render_template(
            'sql_generator.html',
            sql_output='',
            errors=[],
            add_pk=True,
            add_package_fields=True,
        )

    @app.post('/sql_generator')
    def post_sql_generator():
        sql_output, errors, add_pk, add_package_fields = generate_sql_from_config(
            request.files, request.form
        )
        return render_template(
            'sql_generator.html',
            sql_output=sql_output,
            errors=errors,
            add_pk=add_pk,
            add_package_fields=add_package_fields,
        )

    @app.get('/table_config_generator')
    def get_table_config_generator():
        return render_template('table_config_generator.html', errors=[])

    @app.post('/table_config_generator')
    def post_table_config_generator():
        return generate_table_config_from_data_file(request)

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
            return render_template('sql_generator.html', errors=['SQL для скачивания не найден.'])

        return Response(
            sql_content,
            mimetype='application/sql',
            headers={'Content-Disposition': 'attachment; filename=tables.sql'},
        )

    return app

app = create_app()
