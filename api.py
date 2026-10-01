"""
Точка входа FastAPI-приложения.
"""

import uvicorn

from app import app as fastapi_app


app = fastapi_app


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
