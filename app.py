from pathlib import Path

from flask import Flask, Response, render_template, request, send_from_directory

from services.parser import ConfigParseError, parse_tables_config
from services.sql_generator import generate_sql
from services.upload import UploadError, read_uploaded_file
from services.validators import validate_tables


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        sql_output = ''
        errors = []

        if request.method == 'POST':
            try:
                content, filename = read_uploaded_file(request.files.get('config_file'))
                tables = parse_tables_config(content, filename)
                errors = validate_tables(tables)
                if not errors:
                    sql_output = generate_sql(tables)
            except (UploadError, ConfigParseError) as exc:
                errors.append(str(exc))

        return render_template('index.html', sql_output=sql_output, errors=errors)

    @app.get('/download-template')
    def download_template():
        static_dir = Path(app.root_path) / 'static'
        return send_from_directory(
            static_dir,
            'template.xlsm',
            as_attachment=True,
            download_name='template.xlsm',
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
    app.run()
