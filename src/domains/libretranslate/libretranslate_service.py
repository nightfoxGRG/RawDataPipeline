#libretranslate_service.py
import re
import requests

from config.config_loader import get_config


# ---------------------------------------------------------------------------
# Load translation service URL from config/config.toml
# ---------------------------------------------------------------------------
def _get_translation_config() -> str:
    """Возвращает (url) из конфига."""
    cfg = get_config().get('translation', {})
    return cfg.get('libretranslate_url', '')


def _translate_to_english(name: str) -> str:
    """Return *name* translated to English via LibreTranslate if it contains Cyrillic.

    Non-Cyrillic text is returned as-is.
    Raises AppError if the service is unreachable or returns an error.
    """
    if not re.search(r'[а-яёА-ЯЁ]', name):
        return name

    from common.error import AppError

    url  = _get_translation_config()

    payload = {'q': name, 'source': 'ru', 'target': 'en', 'format': 'text', 'api_key': ""}
  
    try:
        response = requests.post(f'{url}/translate', json=payload, timeout=5)
        if response.status_code == 403:
            raise AppError(
                f'Сервис перевода ({url}) вернул 403: требуется API-ключ. '
                f'Укажите api_key в секции [translation] файла config.toml.'
            )
        response.raise_for_status()
        translated = response.json().get('translatedText')
        if not translated:
            raise AppError(f'Сервис перевода ({url}) вернул пустой ответ.')
        return translated
    except AppError:
        raise
    except requests.exceptions.ConnectionError:
        raise AppError(f'Сервис перевода недоступен ({url}).')
    except requests.exceptions.Timeout:
        raise AppError(
            f'Сервис перевода не ответил вовремя ({url}). '
            f'Превышено время ожидания 5 секунд.'
        )
    except Exception as exc:
        raise AppError(f'Ошибка при обращении к сервису перевода ({url}): {exc}')