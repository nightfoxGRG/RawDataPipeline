"""Единый Flask-обработчик прикладных ошибок.

Сервисы выбрасывают `AppError` (или потомков); этот хендлер превращает их
в HTTP-ответ. Формат ответа выбирается по заголовку Accept:
  - `application/json` — JSON `{"errors": [...]}` (используется AJAX-вызовами);
  - иначе рендерится `generator.html` со списком ошибок (используется при
    submit формы со страницы генератора).
"""
from flask import Flask, jsonify, render_template, request

from common.error import AppError

_DEFAULT_STATUS = 422

def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError):
        if _wants_json():
            return jsonify(errors=exc.errors), _DEFAULT_STATUS
        return render_template(
            'generator.html',
            errors=exc.errors,
            sql_output='',
            add_pk=True,
            add_package_fields=True,
        ), _DEFAULT_STATUS


def _wants_json() -> bool:
    accept = request.accept_mimetypes
    if not accept:
        return False
    return accept.best_match(['application/json', 'text/html']) == 'application/json'
