"""
Точка входа для сборки исполняемого файла через PyInstaller.
При запуске открывает браузер и стартует Flask-сервер.
"""
import threading
import webbrowser
import sys
import os


def resource_path(relative_path: str) -> str:
    """Возвращает абсолютный путь к ресурсу (работает и в PyInstaller)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def open_browser():
    webbrowser.open('http://127.0.0.1:8080')


if __name__ == '__main__':
    # Указываем Flask где искать templates и static внутри .exe
    os.environ['FLASK_TEMPLATE_FOLDER'] = resource_path('templates')
    os.environ['FLASK_STATIC_FOLDER'] = resource_path('resources/static')

    from app import create_app

    flask_app = create_app()
    flask_app.template_folder = resource_path('templates')
    flask_app.static_folder = resource_path('resources/static')

    # Открываем браузер через 1.5 секунды после старта
    threading.Timer(1.5, open_browser).start()

    print('DataPipelinePro запущен: http://127.0.0.1:8080')
    print('Для остановки закройте это окно или нажмите Ctrl+C')

    flask_app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)

