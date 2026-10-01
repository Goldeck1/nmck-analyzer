import asyncio

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from app.core.config import settings
from app.schemas.product import (
    ProductRequest,
    TZInitialRequest,
    TZIdeaResponse,
    TZUserChoice,
    TZQuestionResponse,
    TZFinalResponse,
)
from app.services.analyzer import analyze_request
from app.services.tz_service import send_to_n8n_webhook

router = APIRouter(tags=["nmck"])


@router.get("/", tags=["system"])
async def root():
    return {
        "service": "Zakupki Analyzer API",
        "status": "running",
        "version": settings.version,
    }


@router.get("/health", tags=["system"])
async def health():
    return {"status": "healthy"}


@router.post("/analyze-product/")
async def analyze_product(request: ProductRequest):
    docx_bytes, headers = await analyze_request(request)
    return StreamingResponse(
        docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


# ================================
# === ENDPOINTS ДЛЯ ТЕХНИЧЕСКИХ ЗАДАНИЙ ===
# ================================


@router.post("/tz/start", response_model=TZIdeaResponse, tags=["tz"])
async def tz_start(request: TZInitialRequest):
    """
    Начальный запрос для создания ТЗ.
    Отправляет данные в n8n и возвращает варианты от ИИ.
    """
    try:
        # Отправляем данные в n8n
        n8n_data = {
            "name": request.name,
            "characteristics": request.characteristics,
        }
        
        response = await asyncio.to_thread(send_to_n8n_webhook, n8n_data)
        
        # Проверяем формат ответа от n8n
        if "ideas" not in response:
            raise HTTPException(
                status_code=500,
                detail="Неверный формат ответа от n8n: отсутствует поле 'ideas'"
            )
        
        return TZIdeaResponse(ideas=response["ideas"])
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обращении к n8n: {str(e)}"
        )


@router.post("/tz/continue", tags=["tz"])
async def tz_continue(request: TZUserChoice):
    """
    Продолжение диалога с ИИ.
    Отправляет выбор пользователя в n8n и возвращает ТЗ или встречный вопрос.
    """
    try:
        # Отправляем данные в n8n
        n8n_data = {
            "idea_id": request.idea_id,
            "idea_text": request.idea_text,
            "dialog_history": request.dialog_history,
        }
        
        # Добавляем исходные данные, если они есть
        if request.name:
            n8n_data["name"] = request.name
        if request.characteristics:
            n8n_data["characteristics"] = request.characteristics
        
        response = await asyncio.to_thread(send_to_n8n_webhook, n8n_data)
        
        # Проверяем тип ответа
        if "ideas" in response:
            # Получили новые варианты от ИИ
            return TZIdeaResponse(ideas=response["ideas"])
        elif "question" in response:
            # Получили встречный вопрос
            return TZQuestionResponse(question=response["question"])
        elif "technical_specification" in response:
            # Получили финальное ТЗ
            okpd2_codes = response.get("okpd2_codes", [])
            return TZFinalResponse(
                technical_specification=response["technical_specification"],
                okpd2_codes=okpd2_codes if isinstance(okpd2_codes, list) else []
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Неверный формат ответа от n8n: ожидается 'ideas', 'question' или 'technical_specification'"
            )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обращении к n8n: {str(e)}"
        )

