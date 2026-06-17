"""
PROXVEL Backend - Public Release Routes (6B).
Endpoint público para que la futura landing consuma la última APK publicada.
No expone campos internos (file_public_id, created_by).
"""

from fastapi import APIRouter, Query

from app.services import release_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/releases", tags=["Releases (público)"])


@router.get("/latest", summary="Última versión publicada (para la landing)")
def latest_release(
    platform: str = Query("android", description="Plataforma: android | ios"),
):
    latest = release_service.get_latest_public(platform)
    if not latest:
        return success_response(data=None, message="No hay una versión publicada todavía.")
    return success_response(data=latest.model_dump(), message="Última versión publicada")
