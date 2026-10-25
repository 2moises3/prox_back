"""
PROXVEL Backend - Public Release Routes (6B).
Endpoint público para que la futura landing consuma la última APK publicada.
No expone campos internos (file_public_id, created_by).
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import RedirectResponse

from app.services import release_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/releases", tags=["Releases (público)"])


@router.get("/latest/download", summary="Descargar la última APK publicada")
def download_latest_android():
    latest = release_service.get_latest_public("android")
    if not latest or not latest.apk_url:
        raise HTTPException(status_code=404, detail="No hay una APK publicada todavía.")
    return RedirectResponse(
        url=latest.apk_url,
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/latest", summary="Última versión publicada (para la landing)")
def latest_release(
    response: Response,
    platform: str = Query("android", description="Plataforma: android | ios"),
):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    latest = release_service.get_latest_public(platform)
    if not latest:
        return success_response(data=None, message="No hay una versión publicada todavía.")
    return success_response(data=latest.model_dump(), message="Última versión publicada")
