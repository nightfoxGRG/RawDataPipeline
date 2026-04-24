# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec-файл для сборки TableCreator в исполняемый файл.

Сборка:
  Mac/Linux:  pyinstaller TableCreator.spec
  Windows:    pyinstaller TableCreator.spec
"""

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config.toml', '.'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
        'jinja2',
        'jinja2.ext',
        'openpyxl',
        'openpyxl.cell._writer',
        'yaml',
        'toml',
        'services',
        'services.config_generator',
        'services.inferrer',
        'services.models',
        'services.parser',
        'services.sql',
        'services.sql.pg_types',
        'services.sql.sql_generator',
        'services.upload',
        'services.validators',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TableCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # True = показывает консольное окно (удобно для отладки)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='static/icon.ico',  # раскомментируйте и укажите путь к иконке
)

# Для macOS — дополнительно создаёт .app bundle
app = BUNDLE(
    exe,
    name='TableCreator.app',
    icon=None,
    bundle_identifier='com.tablecreator.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)

