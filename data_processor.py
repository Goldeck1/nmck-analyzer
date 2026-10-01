"""
Модуль для обработки данных парсинга госзакупок.
"""
import json
from typing import List, Dict


def format_data_for_llm(formatted_data: List[Dict]) -> Dict:
    """
    Форматирует данные для отправки в LLM.
    
    Args:
        formatted_data: Список словарей с данными о товарах
        
    Returns:
        Словарь в формате для LLM
    """
    if not formatted_data:
        return {
            "original": {"text": "", "characteristic": ""},
            "found": []
        }
    
    # Первый элемент как original
    first_item = formatted_data[0]
    original = {
        "text": first_item.get("text", ""),
        "characteristic": first_item.get("characteristic", "")
    }
    
    # Все элементы в found с id
    found = []
    for idx, item in enumerate(formatted_data):
        found.append({
            "id": idx,
            "text": item.get("text", ""),
            "characteristic": item.get("characteristic", "")
        })
    
    return {
        "original": original,
        "found": found
    }


def filter_approved_items(formatted_data: List[Dict], approved_ids: List[int]) -> List[Dict]:
    """
    Фильтрует одобренные товары по их id.
    
    Args:
        formatted_data: Полный список товаров
        approved_ids: Список id одобренных товаров
        
    Returns:
        Список одобренных товаров
    """
    approved_items = []
    for item_id in approved_ids:
        if 0 <= item_id < len(formatted_data):
            approved_items.append(formatted_data[item_id])
    return approved_items

