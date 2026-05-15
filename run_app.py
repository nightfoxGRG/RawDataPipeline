"""
Точка входа для local-сборки (PyInstaller).

При первом запуске копирует config.local.template.toml в пользовательский каталог
(~/.config/DataPipelinePro/ или %APPDATA%\\DataPipelinePro\\), запускает Flask и
открывает браузер. Onboarding-форма доступна на /setup до тех пор пока config
не валиден.
"""
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser


def resource_path(relative_path: str) -> str:
    """Абсолютный путь к ресурсу внутри PyInstaller-бандла или dev-режима."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def _bootstrap_user_data() -> None:
    """Создать ~/.config/DataPipelinePro/ и положить туда config.local.toml из шаблона."""
    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from common.user_data_paths import ensure_user_data_dir, user_config_file

    user_dir = ensure_user_data_dir()
    target = user_config_file()
    if not target.exists():
        template = resource_path(os.path.join('resources', 'config.local.template.toml'))
        if os.path.exists(template):
            shutil.copy2(template, target)
        else:
            target.write_text(
                '[database]\nhost = "localhost"\nport = 5432\nname = ""\nschema = "data_pipline_schema"\n'
                'user = ""\npassword = ""\n\n'
                '[translation]\nlibretranslate_url = "http://127.0.0.1:50001"\napi_key = ""\n',
                encoding='utf-8',
            )
    print(f'[bootstrap] Пользовательский каталог: {user_dir}')
    print(f'[bootstrap] Config: {target}')


def _wait_for_flask(port: int = 8080, timeout: float = 30.0) -> bool:
    """Опросить порт до тех пор, пока Flask не начнёт принимать соединения."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket() as s:
                s.settimeout(0.5)
                s.connect(('127.0.0.1', port))
            return True
        except OSError:
            time.sleep(0.2)
    return False


def open_browser():
    webbrowser.open('http://127.0.0.1:8080')


def _run_macos_with_splash() -> None:
    """macOS GUI: splash-окно с прогрессом + асинхронная инициализация Flask.

    Splash появляется почти мгновенно после старта Python. Тяжёлые импорты
    (Flask, SQLAlchemy, openpyxl) и create_app() выполняются в фоновом потоке —
    main thread занят NSApplication event loop. Когда Flask готов принимать
    запросы, открывается браузер и splash закрывается.

    NSApp.run() обрабатывает Apple Event quit от Dock → корректное «Завершить».
    """
    try:
        from AppKit import (
            NSApplication, NSApplicationActivationPolicyRegular,
            NSWindow, NSWindowStyleMaskTitled, NSBackingStoreBuffered,
            NSProgressIndicator, NSTextField, NSFont, NSScreen,
        )
        from Foundation import NSMakeRect
    except ImportError as e:
        print(f'[macos] pyobjc недоступен: {e}; fallback без splash')
        _run_macos_fallback()
        return

    ns_app = NSApplication.sharedApplication()
    ns_app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # ── Splash window ─────────────────────────────────────────────────────
    screen = NSScreen.mainScreen().frame()
    w, h = 440, 150
    rect = NSMakeRect(
        (screen.size.width - w) / 2,
        (screen.size.height - h) / 2,
        w, h,
    )
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect, NSWindowStyleMaskTitled, NSBackingStoreBuffered, False,
    )
    window.setTitle_("DataPipelinePro")
    window.setReleasedWhenClosed_(False)

    content = window.contentView()

    title = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 95, 400, 24))
    title.setStringValue_("DataPipelinePro")
    title.setFont_(NSFont.boldSystemFontOfSize_(16))
    title.setEditable_(False)
    title.setBezeled_(False)
    title.setDrawsBackground_(False)
    title.setSelectable_(False)
    content.addSubview_(title)

    status = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 65, 400, 20))
    status.setStringValue_("Запуск…")
    status.setEditable_(False)
    status.setBezeled_(False)
    status.setDrawsBackground_(False)
    status.setSelectable_(False)
    content.addSubview_(status)

    progress = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(20, 30, 400, 20))
    progress.setIndeterminate_(True)
    progress.startAnimation_(None)
    content.addSubview_(progress)

    window.makeKeyAndOrderFront_(None)
    ns_app.activateIgnoringOtherApps_(True)

    # Обновление UI с фонового потока — через performSelectorOnMainThread
    def _set_status(text: str) -> None:
        status.performSelectorOnMainThread_withObject_waitUntilDone_(
            'setStringValue:', text, False,
        )

    def _close_splash() -> None:
        window.performSelectorOnMainThread_withObject_waitUntilDone_(
            'orderOut:', None, False,
        )

    def _startup() -> None:
        try:
            _set_status("Загрузка модулей…")
            from app import create_app

            _set_status("Инициализация приложения…")
            flask_app = create_app()

            _set_status("Запуск веб-сервера…")
            flask_thread = threading.Thread(
                target=lambda: flask_app.run(
                    host='127.0.0.1', port=8080, debug=False, use_reloader=False,
                ),
                daemon=True,
            )
            flask_thread.start()

            _set_status("Ожидание готовности…")
            if not _wait_for_flask():
                _set_status("Не удалось запустить веб-сервер")
                return

            _set_status("Открываем браузер…")
            webbrowser.open('http://127.0.0.1:8080')
            time.sleep(0.3)
            _close_splash()
        except Exception as e:
            import traceback
            traceback.print_exc()
            _set_status(f"Ошибка: {e}")

    threading.Thread(target=_startup, daemon=True).start()

    ns_app.run()  # main thread event loop; обрабатывает Dock Quit


def _run_macos_fallback() -> None:
    """Без pyobjc: TransformProcessType + SIGTERM. В Dock только Force Quit."""
    import ctypes
    import signal

    try:
        class _PSN(ctypes.Structure):
            _fields_ = [('hi', ctypes.c_ulong), ('lo', ctypes.c_ulong)]
        carbon = ctypes.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
        psn = _PSN(0, 1)
        carbon.TransformProcessType(ctypes.byref(psn), 1)
    except Exception as e:
        print(f'[dock] {e}')

    from app import create_app
    flask_app = create_app()

    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()
    threading.Timer(1.5, open_browser).start()

    _stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda s, f: _stop.set())
    try:
        _stop.wait()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    # PyInstaller-сборка автоматически = local-режим (sys.frozen=True)
    _bootstrap_user_data()

    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        _run_macos_with_splash()
    else:
        from app import create_app
        flask_app = create_app()
        threading.Timer(1.5, open_browser).start()
        print('DataPipelinePro запущен: http://127.0.0.1:8080')
        print('Для остановки нажмите Ctrl+C')
        flask_app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
