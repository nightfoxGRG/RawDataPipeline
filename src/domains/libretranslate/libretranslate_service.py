import tomllib
import re
from pathlib import Path
import requests

_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'config.toml'

!!!!!!! переделать  'http://127.0.0.1:50001'
# ---------------------------------------------------------------------------
# Load translation service URL from config/config.toml
# ---------------------------------------------------------------------------
def _load_libretranslate_url() -> str:
    try:
        with open(_CONFIG_PATH, 'rb') as _f:
            _cfg = tomllib.load(_f)
        return _cfg.get('translation', {}).get('libretranslate_url')
    except Exception:
        return 'http://127.0.0.1:50001'

LIBRETRANSLATE_URL: str = _load_libretranslate_url()

def _translate_to_english(name: str) -> str:
    """Return *name* translated to English via LibreTranslate if it contains Cyrillic.

    Non-Cyrillic text is returned as-is.
    Raises ConfigParseError if the service is unreachable or returns an error.
    """
    if not re.search(r'[а-яёА-ЯЁ]', name):
        return name

    from common.error import AppError

    try:
        response = requests.post(
            f'{LIBRETRANSLATE_URL}/translate',
            json={'q': name, 'source': 'ru', 'target': 'en', 'format': 'text'},
            timeout=5,
        )
        response.raise_for_status()
        translated = response.json().get('translatedText')
        if not translated:
            raise AppError(
                f'Сервис перевода ({LIBRETRANSLATE_URL}) вернул пустой ответ.'
            )
        return translated
    except AppError:
        raise
    except requests.exceptions.ConnectionError:
        raise AppError(
            f'Сервис перевода недоступен ({LIBRETRANSLATE_URL}). '
        )
    except requests.exceptions.Timeout:
        raise AppError(
            f'Сервис перевода не ответил вовремя ({LIBRETRANSLATE_URL}). '
            f'Превышено время ожидания 5 секунд.'
        )
    except Exception as exc:
        raise AppError(
            f'Ошибка при обращении к сервису перевода ({LIBRETRANSLATE_URL}): {exc}'
        )