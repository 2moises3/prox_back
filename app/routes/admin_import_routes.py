"""
PROXVEL Backend - Admin Import Routes.
Importación de datos desde el dashboard en dos pasos:
  1. POST /admin/import/{type}/preview — evalúa el archivo y dice qué destinos cambian (no escribe nada).
  2. POST /admin/import/{type}         — aplica el archivo a los destinos elegidos (o a todos).
Tipos: absa, tags, clima, aforo (CSV de la tesis) y catalog (ficha comercial, Excel o CSV).
"""
import io
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import require_admin_or_super_admin
from app.schemas.user_schema import UserResponse
from app.services import import_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/import", tags=["Admin - Import"])
audit_logger = logging.getLogger("proxvel.audit")

_ALLOWED_TYPES = {"absa", "tags", "clima", "aforo", "catalog"}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


async def _read_file(import_type: str, file: UploadFile) -> bytes:
    if import_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo no soportado: '{import_type}'. Válidos: {sorted(_ALLOWED_TYPES)}")
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv o .xlsx")
    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 5 MB)")
    if not content.strip():
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    return content


def _run(db: Session, import_type: str, content: bytes, **kw) -> dict:
    if import_type != "catalog":
        raise HTTPException(status_code=409, detail="El motor V3 utiliza un snapshot científico validado. Sus datos no se sobrescriben desde el dashboard.")
    try:
        return import_service.run_import(db, import_type, content, **kw)
    except (ValueError, UnicodeDecodeError) as e:
        # Archivo mal formado (columna obligatoria ausente, codificación inválida).
        raise HTTPException(status_code=400, detail=f"Archivo no válido: {e}")


@router.get("/catalog/template", summary="Descargar la ficha comercial actual como Excel (plantilla)")
def catalog_template(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "destinos"
    ws.append(list(import_service.CATALOG_COLUMNS))
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in import_service.export_catalog_rows(db):
        ws.append([row[c] for c in import_service.CATALOG_COLUMNS])
    for col, width in zip("ABCDEFGHIJKLMNOPQR", (22, 34, 18, 14, 14, 50, 50, 50, 40, 26, 50, 30, 10, 12, 12, 11, 10)):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ficha_destinos_proxvel.xlsx"'},
    )


@router.post("/{import_type}/preview", summary="Evaluar un archivo sin guardar nada")
async def preview_import(
    import_type: str,
    file: UploadFile = File(..., description="Archivo .csv o .xlsx"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    content = await _read_file(import_type, file)
    result = _run(db, import_type, content, apply=False)
    return success_response(data=result, message="Evaluación del archivo lista")


@router.post("/{import_type}", summary="Aplicar un archivo (actualiza los destinos elegidos)")
async def import_data(
    import_type: str,
    file: UploadFile = File(..., description="Archivo .csv o .xlsx"),
    destinations: str | None = Form(None, description="destination_id separados por coma; vacío = todos"),
    create_new: bool = Form(True, description="Crear los destinos que aún no existen (quedan inactivos)"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    content = await _read_file(import_type, file)
    selected = {d.strip() for d in destinations.split(",") if d.strip()} if destinations else None
    result = _run(db, import_type, content, apply=True, destinations=selected, create_new=create_new)
    audit_logger.info("AUDIT import type=%s user=%s destinations=%s create_new=%s changed=%s",
                      import_type, current_user.user_id, "todos" if selected is None else len(selected),
                      create_new, result.get("summary"))
    return success_response(data=result, message=f"Importación '{import_type}' completada")
