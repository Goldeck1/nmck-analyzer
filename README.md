# Zakupki Analyzer

## Требования
- Python 3.10+
- Установленный Playwright (`playwright install` после зависимостей)

## Установка зависимостей
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install
```

## Запуск локального сервиса
```bash
uvicorn api:app --reload
```

После запуска:
- фронтэнд доступен по адресу `http://localhost:8000`
- API доступно по адресу `http://localhost:8000/api/analyze-product/`

## Архитектура
- `app/__init__.py` — фабрика FastAPI, подключающая CORS, API-роутеры и статику.
- `app/core/config.py` — все настройки (пути, CORS, ключи) в одном месте.
- `app/api/router.py` — единственный роутер (`/`, `/health`, `/api/analyze-product/`).
- `app/services/analyzer.py` — бизнес-логика расчёта НМЦК и формирования ответа.
- `app/schemas/product.py` — Pydantic-модель запроса.
- `frontend/` — статический интерфейс (HTML/CSS/JS), который FastAPI раздаёт как корень сайта.
- Корневые модули (`parser.py`, `zakupki_parser.py`, `data_processor.py`, `report_generator.py`, `llm_client.py`, `okpd2.py`) отвечают за работу с внешними источниками и генерацию отчётов.

## Переменные окружения
- `OKPD2_API_KEY` — при необходимости можно переопределить ключ по умолчанию.
- `LLM_URL`, `LLM_PORT` — настройки сервиса LLM (опционально).
- `TZ_N8N_WEBHOOK_URL` — **обязательно** URL webhook для создания технических заданий через n8n.

### Настройка TZ_N8N_WEBHOOK_URL

Установите переменную окружения перед запуском:

**Linux/Mac:**
```bash
export TZ_N8N_WEBHOOK_URL="https://your-n8n-instance.com/webhook/your-webhook-id"
uvicorn api:app --reload
```

**Windows:**
```cmd
set TZ_N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
uvicorn api:app --reload
```

**Или создайте файл `.env` в корне проекта:**
```
TZ_N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
```

И загрузите его через `python-dotenv` (если установлен) или установите переменную вручную.

