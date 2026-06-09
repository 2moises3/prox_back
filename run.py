"""
PROXVEL Backend - Entry Point
Ejecuta el servidor Uvicorn con la configuración del proyecto.
"""

import uvicorn
from app.config.settings import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
