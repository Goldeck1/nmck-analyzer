"""
Модуль для парсинга госзакупок.
"""
from typing import List, Dict
import okpd2
from parser import parse_zakupki


def parse_zakupki_data(
    search_term: str,
    api_key: str
) -> tuple[List[Dict], List[str]]:
    """
    Парсит данные с сайта госзакупок.
    
    Args:
        search_term: Название товара для поиска
        api_key: API ключ для получения кодов ОКПД2
        
    Returns:
        Кортеж (список отформатированных данных, список кодов ОКПД2)
    """
    # Парсинг данных
    data = parse_zakupki(search_term)
    
    # Получение кодов ОКПД2
    okpd2_codes = okpd2.get_okpd2_codes(search_term, api_key)
    
    # Форматирование данных
    formatted_data = []
    for contract, items in data.items():
        for item in items:
            chars = ""
            for k, v in item.get('characteristics', {}).items():
                if k == "Info" and v == "No KTRU link available":
                    chars = ""
                    break
                chars += f"{k}: {v}; "
            
            formatted_data.append({
                "text": item['name'],
                "ktru_code": item['ktru_code'],
                "quantity": item['quantity'],
                "price": item['price'],
                "total_sum": item['total_sum'],
                "characteristic": chars,
                "contract_url": contract,
                "registry_number": item.get('registry_number', ''),
                "customer_name": item.get('customer_name', ''),
                "total_contract_price": item.get('total_contract_price', ''),
                "contract_date": item.get('contract_date', ''),
                "execution_deadline": item.get('execution_deadline', ''),
                "registry_placement_date": item.get('registry_placement_date', '')
            })
    
    return formatted_data, okpd2_codes

