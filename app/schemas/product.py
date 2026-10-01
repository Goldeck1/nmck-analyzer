from typing import List, Optional

from pydantic import BaseModel


class ProductRequest(BaseModel):
    """Запрос на расчет НМЦК."""

    name: str
    quantity: Optional[int] = None
    characteristic: Optional[str] = None


# ================================
# === СХЕМЫ ДЛЯ ТЕХНИЧЕСКИХ ЗАДАНИЙ ===
# ================================


class TZInitialRequest(BaseModel):
    """Начальный запрос для создания ТЗ."""

    name: str
    characteristics: str


class Idea(BaseModel):
    """Вариант от ИИ."""

    id: int
    text: str


class TZIdeaResponse(BaseModel):
    """Ответ с вариантами от ИИ."""

    ideas: List[Idea]


class TZUserChoice(BaseModel):
    """Выбор пользователя."""

    idea_id: Optional[int] = None
    idea_text: str
    dialog_history: List[dict] = []
    name: Optional[str] = None
    characteristics: Optional[str] = None


class TZQuestionResponse(BaseModel):
    """Встречный вопрос от ИИ."""

    question: str


class TZFinalResponse(BaseModel):
    """Финальный ответ с ТЗ."""

    technical_specification: str
    okpd2_codes: List[str] = []

