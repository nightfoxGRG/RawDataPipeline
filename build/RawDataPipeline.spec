# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для local-сборки RawDataPipeline.

Сборка:
  Mac/Linux:  pyinstaller build/RawDataPipeline.spec
  Windows:    pyinstaller build\\RawDataPipeline.spec

Артефакт идёт в dist/. На старте создаётся ~/.config/RawDataPipeline/ с
config.local.toml — пользователь редактирует через onboarding-форму на /setup.
"""

block_cipher = None

from PyInstaller.utils.hooks import copy_metadata

a = Analysis(
    ['../run_app.py'],
    pathex=['..', '../src'],
    binaries=[],
    datas=[
        ('../resources/templates', 'resources/templates'),
        ('../resources/static', 'resources/static'),
        ('../resources/migrations', 'resources/migrations'),
        ('../resources/config.toml', 'resources'),
        ('../resources/config.local.template.toml', 'resources'),
        *copy_metadata('yoyo-migrations'),  # нужно для importlib_metadata entry_points
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'werkzeug.serving',
        'jinja2',
        'openpyxl',
        'openpyxl.cell._writer',
        'psycopg2',
        'sqlalchemy',
        'sqlalchemy.dialects.postgresql',
        'yoyo',
        'yoyo.backends',
        'yoyo.backends.base',
        'yoyo.backends.core',
        'yoyo.backends.core.postgresql',  # в yoyo 9.x именно здесь PostgresqlBackend
        'importlib_metadata',             # yoyo использует standalone importlib_metadata
        'tomllib',
        # macOS GUI (pyobjc) — нужно для иконки в Dock и пункта «Завершить»
        'objc',
        'AppKit',
        'Foundation',
        'CoreFoundation',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests', 'authlib', 'minio'],
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
    name='RawDataPipeline',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../resources/static/icon.icns',
)

app = BUNDLE(
    exe,
    name='Конвейер Данных.app',
    icon='../resources/static/icon.icns',
    bundle_identifier='com.rawdatapipeline.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'Конвейер Данных',
        'CFBundleDisplayName': 'Конвейер Данных',
    },
)
