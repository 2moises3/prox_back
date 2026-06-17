"""
PROXVEL Backend - App Release Service (6B).
Reglas de negocio para versiones de la APK.
"""
from typing import Any, List, Optional

from app.repositories import db_release_repository as repo
from app.schemas.release_schema import ReleaseResponse, ReleasePublic, PLATFORMS


def list_releases() -> List[ReleaseResponse]:
    return [ReleaseResponse.model_validate(r) for r in repo.get_all()]


def get_release(release_id: int) -> Optional[ReleaseResponse]:
    r = repo.get_by_id(release_id)
    return ReleaseResponse.model_validate(r) if r else None


def create_release(data: dict[str, Any]) -> tuple[Optional[ReleaseResponse], Optional[str]]:
    platform = (data.get("platform") or "android").lower()
    if platform not in PLATFORMS:
        return None, f"Plataforma inválida. Use una de: {', '.join(PLATFORMS)}"
    if not data.get("apk_url"):
        return None, "Se requiere un archivo APK o una apk_url."
    data["platform"] = platform
    r = repo.create(data)
    return ReleaseResponse.model_validate(r), None


def update_release(release_id: int, data: dict[str, Any]) -> Optional[ReleaseResponse]:
    r = repo.update(release_id, data)
    return ReleaseResponse.model_validate(r) if r else None


def set_published(release_id: int, is_published: bool) -> Optional[ReleaseResponse]:
    r = repo.set_published(release_id, is_published)
    return ReleaseResponse.model_validate(r) if r else None


def delete_release(release_id: int) -> Optional[ReleaseResponse]:
    """Elimina la release y, si tenía binario en Cloudinary, lo borra también."""
    r = repo.get_by_id(release_id)
    if not r:
        return None
    public_id = r.file_public_id
    deleted = repo.delete(release_id)
    if deleted and public_id:
        from app.services import cloudinary_service
        cloudinary_service.delete_raw(public_id)
    return ReleaseResponse.model_validate(deleted) if deleted else None


def get_latest_public(platform: str = "android") -> Optional[ReleasePublic]:
    r = repo.get_latest_published(platform)
    return ReleasePublic.model_validate(r) if r else None
