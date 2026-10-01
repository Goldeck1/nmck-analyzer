"""
Сервис для работы с созданием технических заданий через n8n webhook.
"""
from typing import Dict

import requests

from app.core.config import settings


def send_to_n8n_webhook(data: Dict) -> Dict:
    """
    Отправляет данные в n8n webhook для обработки ТЗ.

    Args:
        data: Данные для отправки в n8n

    Returns:
        Ответ от n8n webhook

    Raises:
        ValueError: Если URL webhook не настроен
        requests.RequestException: При ошибке запроса
    """
    if not settings.tz_n8n_webhook_url:
        raise ValueError("TZ_N8N_WEBHOOK_URL не настроен в переменных окружения")

    try:
        print(f"Отправляем запрос к n8n webhook: {settings.tz_n8n_webhook_url}", flush=True)
        response = requests.post(
            settings.tz_n8n_webhook_url,
            json=data,
            timeout=120  # Увеличенный таймаут для работы с LLM
        )
        response.raise_for_status()
        result = response.json()
        print(f"Ответ от n8n webhook: {result}", flush=True)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при обращении к n8n webhook: {e}", flush=True)
        raise

