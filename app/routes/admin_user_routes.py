"""
PROXVEL Backend - Admin User Routes (6B).
Gestión administrativa de usuarios.
- Listar: admin o super_admin.
- Cambiar rol / activar-desactivar: solo super_admin.
- Crear usuarios (admin/traveler): solo super_admin.
- Eliminar usuarios / limpiar datos: solo super_admin.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from pydantic import BaseModel
from app.core.rate_limit import client_ip
from app.core.security import require_admin_or_super_admin, require_super_admin
from app.schemas.user_schema import UserResponse, AdminRoleUpdate, AdminStatusUpdate, AdminUserCreate
from app.services import user_admin_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/users", tags=["Admin - Usuarios"])


def _map_error(error: str) -> HTTPException:
    if "no encontrado" in error:
        return HTTPException(status_code=404, detail=error)
    if "inválido" in error:
        return HTTPException(status_code=422, detail=error)
    # Guardas de negocio (último super_admin, auto-desactivación)
    return HTTPException(status_code=409, detail=error)


@router.get("", summary="Listar usuarios")
def list_users(
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    users = user_admin_service.list_users()
    return success_response(
        data=[u.model_dump() for u in users],
        message="Usuarios obtenidos correctamente",
    )


@router.post("", summary="Crear usuario (solo super_admin)")
def create_user(
    payload: AdminUserCreate,
    current_user: UserResponse = Depends(require_super_admin),
):
    created, error, status_code = user_admin_service.create_user_admin(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)
    return success_response(
        data=created.model_dump(),
        message="Usuario creado correctamente",
    )


@router.patch("/{user_id}/role", summary="Cambiar rol de un usuario (solo super_admin)")
def change_role(
    user_id: str,
    payload: AdminRoleUpdate,
    current_user: UserResponse = Depends(require_super_admin),
):
    updated, error = user_admin_service.change_user_role(
        user_id, payload.role, acting_user_id=current_user.user_id
    )
    if error:
        raise _map_error(error)
    return success_response(data=updated.model_dump(), message="Rol actualizado correctamente")


@router.patch("/{user_id}/status", summary="Activar/desactivar un usuario (solo super_admin)")
def change_status(
    user_id: str,
    payload: AdminStatusUpdate,
    current_user: UserResponse = Depends(require_super_admin),
):
    updated, error = user_admin_service.change_user_status(
        user_id, payload.is_active, acting_user_id=current_user.user_id
    )
    if error:
        raise _map_error(error)
    estado = "activado" if payload.is_active else "desactivado"
    return success_response(data=updated.model_dump(), message=f"Usuario {estado} correctamente")


class ScheduleDeletionRequest(BaseModel):
    reason: str


@router.post("/{user_id}/schedule-deletion", summary="Programar eliminación de un usuario (solo super_admin)")
def schedule_deletion(
    user_id: str,
    payload: ScheduleDeletionRequest,
    current_user: UserResponse = Depends(require_super_admin),
):
    result, error, status_code = user_admin_service.schedule_deletion(
        user_id, payload.reason, current_user.user_id
    )
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)
    return success_response(data=result.model_dump(), message="Eliminación programada correctamente")


@router.post("/{user_id}/cancel-deletion", summary="Cancelar eliminación programada (solo super_admin)")
def cancel_deletion(
    user_id: str,
    current_user: UserResponse = Depends(require_super_admin),
):
    result, error, status_code = user_admin_service.cancel_deletion(user_id)
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)
    return success_response(data=result.model_dump(), message="Eliminación cancelada correctamente")


@router.post("/process-deletions", summary="Procesar eliminaciones vencidas (solo super_admin)")
def process_deletions(
    current_user: UserResponse = Depends(require_super_admin),
):
    result, error, status_code = user_admin_service.process_due_deletions()
    if error:
        raise HTTPException(status_code=status_code or 500, detail=error)
    return success_response(data=result, message=f"Se procesaron {result.get('processed', 0)} eliminaciones.")


@router.delete("/{user_id}", summary="Eliminar usuario o sus datos (solo super_admin)")
def delete_user(
    user_id: str,
    mode: str = Query(..., description="Modo: 'data_only' o 'full'"),
    current_user: UserResponse = Depends(require_super_admin),
):
    result, error, status_code = user_admin_service.delete_user(
        target_user_id=user_id,
        mode=mode,
        acting_user_id=current_user.user_id,
    )
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)

    action_msg = "Cuenta y datos eliminados" if mode == "full" else "Datos del usuario limpiados"
    return success_response(data=result, message=f"{action_msg} correctamente")


@router.post("/{user_id}/reset-password", summary="Restablecer contraseña con una temporal (solo super_admin)")
def reset_password(
    user_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(require_super_admin),
):
    """La contraseña temporal se devuelve una sola vez y no se puede volver a consultar."""
    result, error, status_code = user_admin_service.reset_user_password(
        target_user_id=user_id,
        acting_user_id=current_user.user_id,
        client_ip=client_ip(request),
    )
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)
    response.headers["Cache-Control"] = "no-store"
    return success_response(data=result, message="Contraseña restablecida. Se muestra una sola vez.")


@router.get("/{user_id}/details", summary="Obtener detalles básicos de un usuario (admin)")
def get_user_details(
    user_id: str,
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    result, error, status_code = user_admin_service.get_user_details_admin(user_id)
    if error:
        raise HTTPException(status_code=status_code or 400, detail=error)
    return success_response(data=result, message="Detalles obtenidos correctamente")
