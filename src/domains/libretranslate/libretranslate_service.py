#libretranslate_service.py
import re
import requests

from config.config_loader import get_config


# ---------------------------------------------------------------------------
# Load translation service URL from config/config.toml
# ---------------------------------------------------------------------------
def _get_libretranslate_url() -> str:
    """Возвращает URL LibreTranslate из конфига.
    Использует get_config(), который берёт уже загруженный конфиг из кеша
    или загружает его, если ещё не был загружен.
    """
    return get_config().get('translation', {}).get('libretranslate_url')

def _translate_to_english(name: str) -> str:
    """Return *name* translated to English via LibreTranslate if it contains Cyrillic.

    Non-Cyrillic text is returned as-is.
    Raises ConfigParseError if the service is unreachable or returns an error.
    """
    if not re.search(r'[а-яёА-ЯЁ]', name):
        return name

    from common.error import AppError

    url = _get_libretranslate_url()  # получаем URL при каждом вызове (почти бесплатно)

    try:
        response = requests.post(
            f'{url}/translate',
            json={'q': name, 'source': 'ru', 'target': 'en', 'format': 'text'},
            timeout=5,
        )
        response.raise_for_status()
        translated = response.json().get('translatedText')
        if not translated:
            raise AppError(
                f'Сервис перевода ({url}) вернул пустой ответ.'
            )
        return translated
    except AppError:
        raise
    except requests.exceptions.ConnectionError:
        raise AppError(
            f'Сервис перевода недоступен ({url}). '
        )
    except requests.exceptions.Timeout:
        raise AppError(
            f'Сервис перевода не ответил вовремя ({url}). '
            f'Превышено время ожидания 5 секунд.'
        )
    except Exception as exc:
        raise AppError(
            f'Ошибка при обращении к сервису перевода ({url}): {exc}'
        )