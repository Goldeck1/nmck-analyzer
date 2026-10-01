import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_title: str = "Zakupki Analyzer"
    description: str = "Сервис анализа госзакупок и генерации отчетов"
    version: str = "0.1.0"

    frontend_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "frontend"
    )

    allow_origins: List[str] = ["*"]
    exposed_headers: List[str] = [
        "X-NMCK",
        "X-Avg-Price-Per-Unit",
        "X-Quantity",
        "Content-Disposition",
    ]

    okpd2_api_key: str = Field(
        default_factory=lambda: os.getenv("OKPD2_API_KEY", "931a94067df5e1df2bf91b2026b3568a4de6fbaf")
    )

    tz_n8n_webhook_url: str = Field(
        default_factory=lambda: os.getenv("TZ_N8N_WEBHOOK_URL", "")
    )


settings = Settings()

