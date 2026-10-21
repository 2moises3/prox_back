"""
PROXVEL Backend - Auth Routes.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import get_settings
from app.schemas.auth_schema import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenData
from app.schemas.user_schema import UserResponse
from app.repositories import db_user_repository
from app.utils.hash_util import verify_password, make_dummy_hash_check, password_needs_rehash, get_password_hash
from app.core.security import create_access_token, get_current_user, token_lifetime_for_role
from app.core.rate_limit import client_ip, enforce_login_allowed, record_login_failure, record_login_success
from app.core.rate_limit import enforce_forgot_allowed, enforce_reset_allowed
from app.services import email_service, notification_service, password_reset_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/auth", tags=["Auth"])
audit_logger = logging.getLogger("proxvel.audit")

@router.post("/login", response_model=dict, summary="Autenticar usuario y obtener JWT")
def login(request: LoginRequest, http_request: Request):
    # Bloquea la IP/correo que acumuló demasiados fallos (429)
    enforce_login_allowed(http_request, request.email)

    # Buscar usuario
    user = db_user_repository.get_user_by_email(request.email)
    if not user:
        # Mitigar timing attacks
        make_dummy_hash_check()
        record_login_failure(http_request, request.email)
        audit_logger.info("AUDIT login FAILED ip=%s reason=unknown_account", client_ip(http_request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Verificar contraseña
    if not verify_password(request.password, user.password_hash):
        record_login_failure(http_request, request.email)
        audit_logger.info("AUDIT login FAILED user=%s ip=%s reason=wrong_password", user.user_id, client_ip(http_request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Verificar si el usuario está activo o en eliminación
    if not user.is_active or user.account_status in ("pending_deletion", "deleted"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada o en proceso de eliminación."
        )
        
    # Rehash automático (Migración Perezosa)
    if password_needs_rehash(user.password_hash):
        new_hash = get_password_hash(request.password)
        db_user_repository.update_password_hash(user.user_id, new_hash)
    
    # Usuario válido, crear payload
    user_response = UserResponse.model_validate(user)
    token_payload = {
        "sub": user.user_id,
        "email": user.email
    }
    
    # Crear token
    access_token = create_access_token(data=token_payload, expires_delta=token_lifetime_for_role(user.role))
    record_login_success(http_request, request.email)
    audit_logger.info("AUDIT login OK user=%s ip=%s", user.user_id, client_ip(http_request))
    
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response.model_dump()
        },
        message="Login correcto"
    )

@router.get("/me", response_model=dict, summary="Obtener usuario autenticado actualmente")
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return success_response(
        data=current_user.model_dump(),
        message="Usuario autenticado"
    )


@router.post("/logout-all", response_model=dict, summary="Cerrar sesión en todos mis dispositivos")
def logout_all(http_request: Request, current_user: UserResponse = Depends(get_current_user)):
    """Invalida todos los tokens emitidos hasta ahora (el de este dispositivo también)."""
    db_user_repository.update_user(current_user.user_id, {"password_changed_at": datetime.utcnow()})
    audit_logger.info("AUDIT logout_all user=%s ip=%s", current_user.user_id, client_ip(http_request))
    return success_response(data={}, message="Cerramos tu sesión en todos tus dispositivos.")


@router.post("/change-password", response_model=dict, summary="Cambiar la propia contraseña (exige la actual)")
def change_password(
    payload: ChangePasswordRequest,
    http_request: Request,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Exige la contraseña actual. Cierra todas las demás sesiones del usuario y devuelve un
    token nuevo para que el dispositivo que hizo el cambio siga conectado.
    Los intentos con contraseña actual incorrecta cuentan para el mismo límite que el login.
    """
    ip = client_ip(http_request)
    enforce_login_allowed(http_request, current_user.email)

    user = db_user_repository.get_user_by_id(current_user.user_id)
    if not user or not verify_password(payload.current_password, user.password_hash):
        record_login_failure(http_request, current_user.email)
        audit_logger.warning("AUDIT password_change DENIED user=%s ip=%s reason=wrong_current_password",
                             current_user.user_id, ip)
        # 400 (no 401): la app interpreta un 401 como sesión vencida y cerraría la sesión.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual no es correcta.")

    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="La nueva contraseña debe ser distinta de la actual.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = db_user_repository.update_user(
        user.user_id,
        {"password_hash": get_password_hash(payload.new_password), "password_changed_at": now},
    )
    if not updated:
        raise HTTPException(status_code=500, detail="No pudimos cambiar la contraseña. Intenta nuevamente.")

    record_login_success(http_request, current_user.email)
    audit_logger.info("AUDIT password_change OK user=%s ip=%s sessions_invalidated=true", user.user_id, ip)
    notification_service.notify_user(
        user.user_id, "seguridad", "Cambiaste tu contraseña",
        "Cerramos tus otras sesiones. Si no fuiste tú, restablécela de inmediato.",
        dedupe_key=f"seguridad:cambio:{now.isoformat()}",
    )

    token = create_access_token(
        data={"sub": user.user_id, "email": user.email},
        expires_delta=token_lifetime_for_role(user.role),
    )
    return success_response(
        data={"access_token": token, "token_type": "bearer"},
        message="Contraseña actualizada correctamente",
    )


FORGOT_MESSAGE = (
    "Si el correo está registrado, te enviamos un código de 6 dígitos. "
    "Vence en {minutes} minutos."
)


def _send_reset_email(to: str, name: str | None, code: str) -> None:
    """Corre en segundo plano: la respuesta al cliente no depende (ni revela) el envío."""
    s = get_settings()
    try:
        email_service.send_password_reset_code(to, name, code, s.PASSWORD_RESET_CODE_MINUTES, s.SUPPORT_EMAIL)
    except email_service.EmailSendError:
        pass  # ya quedó en el log; el usuario puede pedir otro código o contactar a soporte


def _require_reset_by_email() -> None:
    s = get_settings()
    if not s.PASSWORD_RESET_BY_EMAIL:
        contacto = f" Escríbenos a {s.SUPPORT_EMAIL}." if s.SUPPORT_EMAIL else ""
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La recuperación por correo estará disponible pronto." + contacto,
        )


@router.post("/forgot-password", response_model=dict, summary="Pedir un código para recuperar la contraseña")
def forgot_password(
    payload: ForgotPasswordRequest,
    http_request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Responde SIEMPRE lo mismo, exista o no el correo (no permite averiguar quién tiene cuenta)."""
    _require_reset_by_email()
    enforce_forgot_allowed(http_request, payload.email)
    result = password_reset_service.request_code(db, payload.email, client_ip(http_request))
    if result is not None:
        user, code = result
        background.add_task(_send_reset_email, user.email, user.name, code)
    s = get_settings()
    return success_response(
        data={"support_email": s.SUPPORT_EMAIL, "expires_minutes": s.PASSWORD_RESET_CODE_MINUTES},
        message=FORGOT_MESSAGE.format(minutes=s.PASSWORD_RESET_CODE_MINUTES),
    )


@router.post("/reset-password", response_model=dict, summary="Cambiar la contraseña con el código recibido por correo")
def reset_password(
    payload: ResetPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    _require_reset_by_email()
    enforce_reset_allowed(http_request, payload.email)
    ok, error = password_reset_service.confirm_code(
        db, payload.email, payload.code, payload.new_password, client_ip(http_request)
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    user = db_user_repository.get_user_by_email(payload.email)
    if user:
        notification_service.notify_user(
            user.user_id, "seguridad", "Restableciste tu contraseña",
            "Cerramos todas tus sesiones. Si no fuiste tú, contacta a soporte de inmediato.",
            dedupe_key=f"seguridad:recuperacion:{datetime.now(timezone.utc).isoformat()}",
        )
    return success_response(data={}, message="Contraseña restablecida. Ya puedes iniciar sesión.")


@router.get("/support-contact", response_model=dict, summary="Contacto de soporte para mostrar en la app")
def support_contact():
    s = get_settings()
    return success_response(
        data={"support_email": s.SUPPORT_EMAIL, "password_reset_by_email": s.PASSWORD_RESET_BY_EMAIL},
        message="Contacto de soporte",
    )
