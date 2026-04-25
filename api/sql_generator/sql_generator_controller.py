from flask import Blueprint, render_template, request

from api.sql_generator.sql_generator_service import generate_sql_from_config

sql_generator_bp = Blueprint('sql_generator', __name__)


@sql_generator_bp.get('/sql_generator_from_config')
def get_sql_generator_from_config():
    return render_template(
        'index.html',
        sql_output='',
        errors=[],
        add_pk=True,
        add_package_fields=True,
    )


@sql_generator_bp.post('/sql_generator_from_config')
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
