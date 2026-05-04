#libretranslate_service.py
import re

import requests

from common.singleton_meta import SingletonMeta
from config.config_loader import get_config


class LibreTranslateService(metaclass=SingletonMeta):

    def translate_to_english(self, name: str) -> str:
        """Перевести *name* на английский через LibreTranslate, если содержит кириллицу."""
        if not re.search(r'[а-яёА-ЯЁ]', name):
            return name

        from common.error import AppError

        url = self._get_translation_url()
        payload = {'q': name, 'source': 'ru', 'target': 'en', 'format': 'text', 'api_key': ''}

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

    @staticmethod
    def _get_translation_url() -> str:
        return get_config().get('translation', {}).get('libretranslate_url', '')
