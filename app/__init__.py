from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from app.api.router import router as api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        description=settings.description,
        version=settings.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=settings.exposed_headers,
    )

    app.include_router(api_router, prefix="/api")

    if settings.frontend_dir.exists():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    else:
        @app.get("/", include_in_schema=False)
        async def frontend_placeholder():
            return JSONResponse(
                {"message": "Добавьте директорию frontend со статикой фронтенда."},
                status_code=503,
            )

    return app


app = create_app()

