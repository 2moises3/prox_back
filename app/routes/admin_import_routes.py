"""
PROXVEL Backend - Admin Import Routes.
POST /admin/import/{type} — importa CSV desde el dashboard a la BD.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import get_current_user, require_admin_or_super_admin
from app.schemas.user_schema import UserResponse
from app.services.import_service import ImportType, import_csv
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/import", tags=["Admin - Import"])

_ALLOWED_TYPES: set[ImportType] = {"absa", "tags", "clima", "aforo"}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/{import_type}",
    summary="Importar CSV a la BD",
    description=(
        "Sube un archivo CSV y lo importa directamente a la BD. "
        "Nuevos destinos detectados se crean como is_active=False. "
        "Tipos soportados: absa, tags. (clima y aforo: fase posterior)"
    ),
)
async def import_data(
    import_type: str,
    file: UploadFile = File(..., description="Archivo CSV"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    if import_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo no soportado: '{import_type}'. Válidos: {sorted(_ALLOWED_TYPES)}",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 5 MB)")
    if not content.strip():
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    result = import_csv(db, import_type, content)  # type: ignore[arg-type]
    return success_response(data=result, message=f"Importación '{import_type}' completada")
