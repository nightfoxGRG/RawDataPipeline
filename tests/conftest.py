# conftest.py
import os
import sys
from pathlib import Path

os.environ.setdefault('FLASK_TESTING', 'true')

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root / 'src'))
sys.path.insert(0, str(_root))
