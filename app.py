from pathlib import Path

from flask import Flask, Response, render_template, request, send_from_directory

from services.config_generator import generate_excel_config_v2
from services.inferrer import ALLOWED_DATA_EXTENSIONS, infer_columns, read_data_file
from services.models import ConfigParseError
from services.parser import parse_tables_config
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

    @app.get('/inferrer')
    def inferrer():
        return render_template('inferrer.html', errors=[])

    @app.post('/inferrer/generate')
    def inferrer_generate():
        file_storage = request.files.get('data_file')
        if file_storage is None or not file_storage.filename:
            return render_template('inferrer.html', errors=['Не выбран файл данных.'])

        filename = file_storage.filename
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_DATA_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_DATA_EXTENSIONS))
            return render_template(
                'inferrer.html',
                errors=[f'Поддерживаются только файлы: {allowed}'],
            )

        content = file_storage.read()
        if not content:
            return render_template('inferrer.html', errors=['Загруженный файл пустой.'])

        try:
            table_name, headers, rows = read_data_file(content, filename)
            columns = infer_columns(headers, rows)
            xlsx_bytes = generate_excel_config_v2(table_name, columns)
        except (ConfigParseError, Exception) as exc:
            return render_template('inferrer.html', errors=[str(exc)])

        download_name = f'{table_name}_config.xlsx'
        return Response(
            xlsx_bytes,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={download_name}'},
        )

    @app.get('/download-template')
    def download_template():
        static_dir = Path(app.root_path) / 'static'
        return send_from_directory(
            static_dir,
            'TablesConfig.xlsm',
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
