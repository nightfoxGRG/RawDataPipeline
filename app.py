#app.py
import sys
import os

from common.db_decorator.db_context import DbContext

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

from flask import Flask, Response, g, redirect, render_template, request, send_from_directory, session, url_for
from common.error import AppError
from common.error_handler import register_error_handlers
from common.project_paths import ProjectPaths
from common.context_service import ContextService
from common.keycloak_auth import init_oauth, oauth
from config.db_migration_yoyo.db_migrate_config_at_start import run_migrations_on_start
from domains.generator.sql_generator_service import SqlGeneratorService
from domains.configurator.table_config_generator_service import TableConfigGeneratorService
from domains.source_to_table.source_to_table_service import SourceToTableService
from domains.source_to_table.source_to_table_schema_service import SourceToTableSchemaService
from domains.loader.loader_by_table_config_service import LoaderByTableConfigService
from domains.loader.loader_by_directory_service import LoaderByDirectoryService
from domains.analyzer.analyzer_service import AnalyzerService
from domains.db_setting.db_setting_service import DbSettingService
from domains.db_setting_credential.db_setting_credential_service import DbSettingCredentialService
from domains.project.project_service import ProjectService
from domains.users.user_setting_service import UserSettingService
from domains.users.users_service import UsersService
from config.config_loader import get_config

_SYSTEM_SCHEMA = 'system'

_sql_generator = SqlGeneratorService()
_table_config_generator = TableConfigGeneratorService()
_source_to_table_service = SourceToTableService()
_source_to_table_schema_service = SourceToTableSchemaService()
_loader_by_table_config_service = LoaderByTableConfigService()
_loader_by_directory_service = LoaderByDirectoryService()
_analyzer_service = AnalyzerService()
_db_setting_service = DbSettingService()
_db_setting_credential_service = DbSettingCredentialService()
_project_service = ProjectService()
_user_setting_service = UserSettingService()
_users_service = UsersService()

_PUBLIC_ENDPOINTS = {'login', 'callback', 'logout', 'static'}


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ProjectPaths.TEMPLATES),
        static_folder=str(ProjectPaths.STATIC)
    )

    cfg = get_config()

    app.secret_key = cfg.get('app', {}).get('secret_key', 'dev-secret-change-me')

    _run_mode = 'local' if getattr(sys, 'frozen', False) else 'server'
    _project_name = cfg.get('app', {}).get('project_name', 'DataPipelinePro')

    import os
    if not os.environ.get('FLASK_TESTING'):
        run_migrations_on_start()

    init_oauth(app)
    register_error_handlers(app)

    @app.before_request
    def load_user_context():
        g.current_user = None
        if request.endpoint in _PUBLIC_ENDPOINTS:
            return
        token = session.get('access_token')
        if not token:
            return redirect(url_for('login'))
        context_service = ContextService()
        g.current_user = context_service.load_user_context(token)
        if g.current_user is None:
            session.clear()
            return redirect(url_for('login'))

    @app.context_processor
    def inject_globals():
        return {
            'run_mode': _run_mode,
            'project_name': _project_name,
            'current_user': getattr(g, 'current_user', None),
        }

    @app.teardown_request
    def teardown_request(error=None):
        g.current_user = None
        if DbContext().is_active():
            DbContext().clear()

    # ── Аутентификация ────────────────────────────────────────────────────

    @app.get('/login')
    def login():
        redirect_uri = url_for('callback', _external=True)
        return oauth.keycloak.authorize_redirect(redirect_uri)

    @app.get('/callback')
    def callback():
        token = oauth.keycloak.authorize_access_token()
        userinfo = token.get('userinfo') or {}
        subject_id = userinfo.get('email')
        if not subject_id:
            return redirect(url_for('login'))
        _users_service.get_or_create_user(
            subject_id=subject_id,
            first_name=userinfo.get('given_name') or '',
            last_name=userinfo.get('family_name') or '',
            email=userinfo.get('email') or '',
        )
        session['access_token'] = token['access_token']
        return redirect(url_for('index'))

    @app.get('/logout')
    def logout():
        session.clear()
        kc = get_config().get('keycloak', {})
        logout_url = (
            f"{kc.get('server_url', '')}/realms/{kc.get('realm', 'master')}"
            f"/protocol/openid-connect/logout"
            f"?post_logout_redirect_uri={url_for('login', _external=True)}"
            f"&client_id={kc.get('client_id', '')}"
        )
        return redirect(logout_url)

    # ── Параметризатор ────────────────────────────────────────────────────

    @app.route('/', methods=['GET'])
    def index():
        return render_template('configurator.html')

    @app.get('/parametrizer')
    def get_parametrizer():
        return render_template('parametrizer.html')

    @app.get('/parametrizer/db-settings')
    def get_db_settings():
        return _db_setting_service.list_settings()

    @app.post('/parametrizer/db-settings')
    def post_db_setting():
        return _db_setting_service.save_setting(request.get_json(force=True, silent=True) or {})

    @app.delete('/parametrizer/db-settings/<int:setting_id>')
    def delete_db_setting(setting_id: int):
        return _db_setting_service.delete_setting(setting_id)

    @app.get('/parametrizer/db-credentials')
    def get_db_credentials():
        return _db_setting_credential_service.list_credentials()

    @app.post('/parametrizer/db-credentials')
    def post_db_credential():
        return _db_setting_credential_service.save_credential(request.get_json(force=True, silent=True) or {})

    @app.get('/parametrizer/projects')
    def get_projects():
        return _project_service.list_projects()

    @app.post('/parametrizer/projects')
    def post_project():
        return _project_service.save_project(request.get_json(force=True, silent=True) or {})

    @app.delete('/parametrizer/projects/<int:project_id>')
    def delete_project(project_id: int):
        return _project_service.delete_project(project_id)

    @app.get('/parametrizer/actual-project')
    def get_actual_project():
        return _user_setting_service.get_actual_project()

    @app.post('/parametrizer/actual-project')
    def post_actual_project():
        return _user_setting_service.set_actual_project(request.get_json(force=True, silent=True) or {})

    # ── Маршрутизатор ─────────────────────────────────────────────────────

    @app.get('/router')
    def get_router():
        return render_template('router.html')

    @app.post('/source_to_table/generate_from_config')
    def post_source_to_table_generate_from_config():
        return _source_to_table_service.generate_mapping_from_config(request.form)

    @app.get('/source_to_table/schema/tables')
    def get_source_to_table_schema_tables():
        return _source_to_table_schema_service.list_project_tables()

    @app.get('/source_to_table/schema/table-configs')
    def get_source_to_table_schema_table_configs():
        return _source_to_table_schema_service.list_table_configs(request.args.get('table_name', ''))

    @app.post('/source_to_table/schema/table-configs')
    def post_source_to_table_schema_table_config():
        return _source_to_table_schema_service.create_table_config(
            request.args.get('table_name', ''),
            request.get_json(silent=True) or {},
        )

    @app.patch('/source_to_table/schema/table-configs/<int:config_id>')
    def patch_source_to_table_schema_table_config(config_id):
        return _source_to_table_schema_service.rename_table_config(
            config_id,
            request.get_json(silent=True) or {},
        )

    @app.get('/source_to_table/schema/mapping')
    def get_source_to_table_schema_mapping():
        config_id_raw = request.args.get('config_id', '')
        try:
            config_id = int(config_id_raw) if config_id_raw else None
        except ValueError:
            config_id = None
        return _source_to_table_schema_service.get_table_mapping(
            request.args.get('table_name', ''),
            config_id,
        )

    @app.post('/source_to_table/schema/mapping')
    def post_source_to_table_schema_mapping():
        return _source_to_table_schema_service.save_mapping(request.get_json(silent=True) or {})

    @app.delete('/source_to_table/schema/mapping')
    def delete_source_to_table_schema_mapping():
        return _source_to_table_schema_service.delete_mapping(request.args.get('table_name', ''))

    # ── Загружатор ────────────────────────────────────────────────────────

    @app.get('/loader')
    def get_loader():
        return render_template('loader.html')

    @app.post('/loader/load_by_table_config_from_directory')
    def post_loader_load_by_table_config_from_directory():
        return _loader_by_table_config_service.load_from_directory(request)

    @app.get('/loader/directory/configs')
    def get_loader_directory_configs():
        return _loader_by_directory_service.list_configs()

    @app.post('/loader/directory/load')
    def post_loader_directory_load():
        return _loader_by_directory_service.load_from_directory(request)

    # ── Анализатор ────────────────────────────────────────────────────────

    @app.get('/analyzer')
    def get_analyzer():
        return render_template('analyzer.html')

    @app.get('/analyzer/tables')
    def get_analyzer_tables():
        from flask import jsonify
        tables = _analyzer_service.get_tables()
        return jsonify(tables=tables)

    @app.post('/analyzer/run')
    def post_analyzer_run():
        from flask import jsonify, send_file
        import io
        body = request.get_json(force=True, silent=True) or {}
        tables = body.get('tables') or []
        chunk_size = int(body.get('chunk_size') or 1000)
        xlsx_bytes = _analyzer_service.analyze_tables(tables, chunk_size)
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='analyzer_report.xlsx',
        )

    # ── Генератор ─────────────────────────────────────────────────────────

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

    # ── Конфигуратор ──────────────────────────────────────────────────────

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
    app.run(host='localhost', port=8080, debug=True, use_reloader=False)
