"""
PROXVEL Backend - Cloudinary Service.
"""
import logging
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api

from fastapi import UploadFile, HTTPException
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Cloudinary if keys are present
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )
    logger.info("Cloudinary configurado correctamente.")
else:
    logger.warning("Faltan variables de entorno de Cloudinary. Las subidas fallarán.")

def build_public_id(destination_id: str, media_type: str) -> str:
    """Genera un public_id único para Cloudinary."""
    folder = settings.CLOUDINARY_FOLDER.strip("/")
    unique_id = uuid.uuid4().hex[:8]
    if media_type == "cover":
        return f"{folder}/{destination_id}/cover/{unique_id}"
    elif media_type == "gallery":
        return f"{folder}/{destination_id}/gallery/{unique_id}"
    else:
        return f"{folder}/{destination_id}/other/{unique_id}"

def upload_destination_image(file: UploadFile, destination_id: str, media_type: str) -> dict:
    """Sube una imagen a Cloudinary."""
    if not settings.CLOUDINARY_CLOUD_NAME:
        raise HTTPException(status_code=500, detail="Cloudinary no está configurado en el backend.")
        
    public_id = build_public_id(destination_id, media_type)
    
    try:
        response = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            resource_type="image",
            overwrite=True
        )
        return {
            "secure_url": response.get("secure_url"),
            "public_id": response.get("public_id"),
            "format": response.get("format"),
            "resource_type": response.get("resource_type"),
            "bytes": response.get("bytes")
        }
    except Exception as e:
        logger.error(f"Error subiendo imagen a Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Fallo al subir la imagen al servidor multimedia.")

def upload_announcement_image(file: UploadFile, announcement_id: int) -> dict:
    """Sube la imagen de fondo de un anuncio interno a Cloudinary."""
    if not settings.CLOUDINARY_CLOUD_NAME:
        raise HTTPException(status_code=500, detail="Cloudinary no está configurado en el backend.")

    folder = settings.CLOUDINARY_FOLDER.strip("/").split("/")[0]  # carpeta raíz del proyecto
    unique_id = uuid.uuid4().hex[:8]
    public_id = f"{folder}/announcements/{announcement_id}/{unique_id}"

    try:
        response = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            resource_type="image",
            overwrite=True,
        )
        return {
            "secure_url": response.get("secure_url"),
            "public_id": response.get("public_id"),
        }
    except Exception as e:
        logger.error(f"Error subiendo imagen de anuncio a Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Fallo al subir la imagen del anuncio.")


def upload_release_apk(file: UploadFile, version_name: str) -> dict:
    """Sube una APK a Cloudinary como recurso 'raw'.

    Nota: el plan gratuito de Cloudinary limita el tamaño de archivos raw
    (~10MB). Para APKs grandes conviene usar storage dedicado; en ese caso el
    admin puede pegar una apk_url externa en vez de subir el archivo.
    """
    if not settings.CLOUDINARY_CLOUD_NAME:
        raise HTTPException(status_code=500, detail="Cloudinary no está configurado en el backend.")

    folder = settings.CLOUDINARY_FOLDER.strip("/").split("/")[0]
    unique_id = uuid.uuid4().hex[:8]
    safe_version = version_name.replace(".", "_").replace("/", "-")
    public_id = f"{folder}/releases/{safe_version}_{unique_id}"

    try:
        response = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            resource_type="raw",
            overwrite=True,
        )
        return {
            "secure_url": response.get("secure_url"),
            "public_id": response.get("public_id"),
            "bytes": response.get("bytes"),
        }
    except Exception as e:
        logger.error(f"Error subiendo APK a Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Fallo al subir la APK al servidor de archivos.")


def delete_raw(public_id: str) -> bool:
    """Elimina un recurso raw (ej. APK) de Cloudinary."""
    if not settings.CLOUDINARY_CLOUD_NAME or not public_id:
        return False
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="raw")
        return result.get("result") == "ok"
    except Exception as e:
        logger.error(f"Error borrando raw de Cloudinary: {e}")
        return False


def delete_image(public_id: str) -> bool:
    """Elimina una imagen de Cloudinary."""
    if not settings.CLOUDINARY_CLOUD_NAME:
        return False

    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception as e:
        logger.error(f"Error borrando imagen de Cloudinary: {e}")
        return False
