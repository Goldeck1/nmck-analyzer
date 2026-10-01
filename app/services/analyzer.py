import asyncio
import io
import urllib.parse
import uuid
from typing import Dict, Tuple

from fastapi import HTTPException

from app.core.config import settings
from app.schemas.product import ProductRequest
from data_processor import filter_approved_items, format_data_for_llm
from llm_client import send_to_llm_webhook
from report_generator import generate_report_from_approved
from zakupki_parser import parse_zakupki_data


async def analyze_request(request: ProductRequest) -> Tuple[io.BytesIO, Dict[str, str]]:
    """
    Полный цикл обработки запроса на расчет НМЦК.
    """
    formatted_data, okpd2_codes = await asyncio.to_thread(
        parse_zakupki_data,
        request.name,
        settings.okpd2_api_key,
    )

    if not formatted_data:
        raise HTTPException(status_code=404, detail="Не найдено данных по указанному товару")

    llm_data = format_data_for_llm(formatted_data)
    llm_response = await asyncio.to_thread(send_to_llm_webhook, llm_data)

    checked_ids = [item["id"] for item in llm_response.get("checked", [])]
    approved_items = filter_approved_items(formatted_data, checked_ids)
    if not approved_items:
        raise HTTPException(status_code=400, detail="LLM не одобрил ни одного товара")

    docx_bytes, nmck, avg_price = await asyncio.to_thread(
        generate_report_from_approved,
        approved_items,
        request.name,
        okpd2_codes,
        request.quantity,
        request.characteristic,
    )

    headers = build_headers(request.name, request.quantity, nmck, avg_price)
    docx_bytes.seek(0)
    return docx_bytes, headers


def build_headers(name: str, quantity: int | None, nmck: float | None, avg_price: float | None) -> Dict[str, str]:
    filename_ascii = f"report_{uuid.uuid4().hex[:8]}.docx"
    filename_encoded = urllib.parse.quote(name.encode("utf-8"))
    content_disposition = f"attachment; filename={filename_ascii}; filename*=UTF-8''{filename_encoded}.docx"

    headers = {"Content-Disposition": content_disposition}
    if nmck is not None:
        headers["X-NMCK"] = str(round(nmck, 2))
    if avg_price is not None:
        headers["X-Avg-Price-Per-Unit"] = str(round(avg_price, 2))
    if quantity is not None:
        headers["X-Quantity"] = str(quantity)

    return headers

