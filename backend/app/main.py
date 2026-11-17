"""后端入口：uvicorn app.main:app"""
import uvicorn

from .config import get_settings
from .api import app  # noqa: F401

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
