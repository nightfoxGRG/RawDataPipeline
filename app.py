#app.py
import sys
import os

from common.db_decorator.db_context import DbContext

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

import base64
import json

from flask import Flask, Response, g, render_template, request, send_from_directory
from common.error import AppError
from common.error_handler import register_error_handlers
from common.project_paths import ProjectPaths
from common.context_service import ContextService
from config.db_migration_yoyo.db_migrate_config_at_start import run_migrations_on_start
from domains.generator.sql_generator_service import SqlGeneratorService
from domains.configurator.table_config_generator_service import TableConfigGeneratorService
from domains.source_to_table.source_to_table_service import SourceToTableService
from domains.source_to_table.source_to_table_schema_service import SourceToTableSchemaService
from config.config_loader import get_config

_SYSTEM_SCHEMA = 'system'

_sql_generator = SqlGeneratorService()
_table_config_generator = TableConfigGeneratorService()
_source_to_table_service = SourceToTableService()
_source_to_table_schema_service = SourceToTableSchemaService()


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

    @app.before_request
    def load_user_context():
        g.current_user = None

# до настройки аутентификации, для разработки и тестов можно использовать заглушку с фиксированным токеном
        # auth_header = request.headers.get('Authorization', '')
        # if not auth_header.lower().startswith('bearer '):
        #     return
        # token = auth_header.split(' ', 1)[1].strip()

        def _generate_stub_token():
            header = {"alg": "none", "typ": "JWT"}
            payload = {"sub": "LOCAL_USER"}
            header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
            payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
            signature = ""
            return f"{header_b64}.{payload_b64}.{signature}"

        token = _generate_stub_token()

        context_service = ContextService()
        g.current_user = context_service.load_user_context(token)

    @app.context_processor
    def inject_globals():
        return {
            'run_mode': _run_mode,
            'project_name': _project_name,
            'current_user': getattr(g, 'current_user', None),
        }

    @app.teardown_request
    def teardown_request(error=None):
        # Явный сброс контекста после запроса
        g.current_user = None
        """Очищает контекст БД после каждого запроса."""
        if DbContext().is_active():
            DbContext().clear()

    @app.route('/', methods=['GET'])
    def index():
        return render_template('configurator.html')

    @app.get('/parametrizer')
    def get_parametrizer():
        return render_template('parametrizer.html')

    @app.get('/router')
    def get_router():
        return render_template('router.html')

    @app.post('/source_to_table/generate_from_config')
    def post_source_to_table_generate_from_config():
        return _source_to_table_service.generate_mapping_from_config(request.form)

    @app.get('/source_to_table/schema/tables')
    def get_source_to_table_schema_tables():
        return _source_to_table_schema_service.list_project_tables()

    @app.get('/source_to_table/schema/mapping')
    def get_source_to_table_schema_mapping():
        return _source_to_table_schema_service.get_table_mapping(
            request.args.get('table_name', '')
        )

    @app.post('/source_to_table/schema/mapping')
    def post_source_to_table_schema_mapping():
        return _source_to_table_schema_service.save_mapping(request.get_json(silent=True) or {})

    @app.delete('/source_to_table/schema/mapping')
    def delete_source_to_table_schema_mapping():
        return _source_to_table_schema_service.delete_mapping(request.args.get('table_name', ''))

    @app.get('/loader')
    def get_loader():
        return render_template('loader.html')

    @app.get('/analyzer')
    def get_analyzer():
        return render_template('analyzer.html')

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
        sql_output, add_pk, add_package_fields = _sql_generator.generate_sql_from_system_config(request.form)
        return render_template(
            'generator.html',
            sql_output=sql_output,
            add_pk=add_pk,
            add_package_fields=add_package_fields,
        )

    @app.post('/sql_execute')
    def post_sql_execute():
        return _sql_generator.execute_sql_in_working_db(request.form)

    @app.get('/configurator')
    def get_configurator():
        return render_template('configurator.html')

    @app.post('/table_config_generator')
    def post_table_config_generator():
        return _table_config_generator.generate_table_config_from_data_file(request)

    @app.post('/table_config_generator_from_directory')
    def post_table_config_generator_from_directory():
        return _table_config_generator.generate_table_config_from_directory(request)

    @app.post('/table_config_upload')
    def post_table_config_upload():
        return _table_config_generator.upload_table_config_file(request)

    @app.get('/table_config_download_system')
    def get_table_config_download_system():
        return _table_config_generator.download_table_config_system()

    @app.get('/table_config_validate_system')
    def get_table_config_validate_system():
        return _table_config_generator.validate_table_config_system()

    @app.post('/table_config_validate_local')
    def post_table_config_validate_local():
        return _table_config_generator.validate_table_config_local(request)

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
