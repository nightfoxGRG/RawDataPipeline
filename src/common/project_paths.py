# project_paths.py
import sys
from pathlib import Path


class ProjectPaths:
    """Централизованное управление путями проекта.

    В PyInstaller-сборке ресурсы лежат в sys._MEIPASS — это автоматически
    распакованный временный каталог с папкой 'resources'.
    """

    if hasattr(sys, '_MEIPASS'):
        ROOT = Path(sys._MEIPASS)
    else:
        # src/common/project_paths.py → src/common/ → src/ → корень
        ROOT = Path(__file__).parent.parent.parent

    CONFIG = ROOT / 'resources'
    MIGRATIONS = ROOT / 'resources' / 'migrations'
    TEMPLATES = ROOT / 'resources' / 'templates'
    STATIC = ROOT / 'resources' / 'static'
    TABLE_CONFIG_TEMPLATE = STATIC / 'TablesConfig.xlsm'
