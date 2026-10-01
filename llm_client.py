"""
Модуль для работы с LLM сервисом.
"""
import os
from typing import Dict

import requests

# Webhook URL для LLM (можно переопределить через переменную окружения)
LLM_WEBHOOK_URL = os.getenv(
    "LLM_WEBHOOK_URL",
    ""
)


def send_to_llm(data: Dict) -> Dict:
    """
    Отправляет данные в LLM для проверки.
    
    Args:
        data: Данные в формате {"original": {...}, "found": [...]}
        
    Returns:
        Ответ от LLM в формате {"checked": [{"id": 1}, ...]}
    """
    # Заглушка - возвращает те же данные в нужном формате
    # В реальной реализации здесь будет запрос к LLM сервису
    
    # Пример заглушки: одобряем первые 3 элемента
    checked_ids = []
    found_items = data.get("found", [])
    
    # Заглушка: одобряем первые 3 элемента (или все, если меньше 3)
    for i in range(len(found_items)):
        checked_ids.append({"id": i})
    print(f"Заглушка: одобренные ID: {checked_ids}", flush=True)
    return {"checked": checked_ids}


def send_to_llm_webhook(data: Dict) -> Dict:
    """
    Реальная отправка данных в LLM через webhook (на основе test.py).
    
    Args:
        data: Данные в формате {"original": {...}, "found": [...]}
        
    Returns:
        Ответ от LLM
    """
    if not LLM_WEBHOOK_URL:
        return send_to_llm(data)
    try:
        print(f"Отправляем запрос к LLM webhook: {LLM_WEBHOOK_URL}", flush=True)
        response = requests.post(
            LLM_WEBHOOK_URL,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        print(f"Ответ от LLM webhook: {result}", flush=True)
        return result
    except Exception as e:
        print(f"Ошибка при обращении к LLM webhook: {e}", flush=True)
        # Fallback на заглушку
        return send_to_llm(data)

