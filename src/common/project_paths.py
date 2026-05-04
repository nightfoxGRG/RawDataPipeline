# project_paths.py
from pathlib import Path

class ProjectPaths:
    """Централизованное управление путями проекта"""
    
    # Корень проекта (там, где находится этот файл)
    ROOT = Path(__file__).parent.parent.parent
    
    # Подпапки
    CONFIG = ROOT / 'resources'
    MIGRATIONS = ROOT / 'resources' / 'migrations'
    TEMPLATES = ROOT / 'resources' / 'templates'
    STATIC = ROOT /'resources' / 'static'
