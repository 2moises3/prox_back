"""
PROXVEL - Prueba el envío de correo con la configuración actual (.env).

Uso (desde proxvel_backend, dentro del contenedor o con el venv):
    python scripts/test_email.py tu_correo@ejemplo.com

Con EMAIL_BACKEND=console solo escribe el correo en el log. Con EMAIL_BACKEND=smtp (Resend, Gmail,
Brevo...) lo envía de verdad y te dice si falló y por qué. No imprime contraseñas.
"""
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config.settings import get_settings
from app.services import email_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print("Uso: python scripts/test_email.py destino@ejemplo.com")
        return 2
    s = get_settings()
    print(f"EMAIL_BACKEND = {s.EMAIL_BACKEND}")
    if s.EMAIL_BACKEND.lower() == "smtp":
        print(f"SMTP_HOST     = {s.SMTP_HOST}:{s.SMTP_PORT}  usuario={s.SMTP_USER}  desde={s.SMTP_FROM}")
    try:
        email_service.send_password_reset_code(sys.argv[1], "Prueba", "123456", s.PASSWORD_RESET_CODE_MINUTES, s.SUPPORT_EMAIL)
    except email_service.EmailSendError as e:
        print(f"FALLÓ: {e}. Revisa el log de arriba (host, puerto, usuario/clave o dominio no verificado).")
        return 1
    print("OK: correo de prueba enviado." if s.EMAIL_BACKEND.lower() == "smtp" else "OK (modo consola: no se envió nada).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
