import requests


def get_okpd2_codes(query, api_key):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/okpd2"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}"
    }

    payload = {
        "query": query
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Извлекаем коды из ответа
        codes = []
        for suggestion in result.get('suggestions', []):
            code = suggestion.get('data', {}).get('kod')
            if code:
                codes.append(code)

        return codes

    except requests.exceptions.RequestException as e:
        print(f"Произошла ошибка при выполнении запроса: {e}")
        return []


# Использование
