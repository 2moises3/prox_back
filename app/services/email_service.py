"""
PROXVEL Backend - Envío de correos.

EMAIL_BACKEND:
  console : (desarrollo) no envía nada: escribe el correo en el log del backend, con el código.
  smtp    : envío real por SMTP (Gmail con contraseña de aplicación, Resend SMTP, Brevo, etc.).
  memory  : (pruebas) guarda los correos en OUTBOX.

En producción (APP_ENV=production) solo se permite smtp.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config.settings import get_settings

logger = logging.getLogger("proxvel.email")

# Solo para EMAIL_BACKEND=memory (pruebas).
OUTBOX: list[dict] = []


class EmailSendError(Exception):
    pass


def _backend() -> str:
    return get_settings().EMAIL_BACKEND.strip().lower()


def send_email(to: str, subject: str, text: str) -> None:
    backend = _backend()
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "text": text})
        return
    if backend == "console":
        logger.info("EMAIL (consola, no se envía) | para=%s | asunto=%s\n%s", to, subject, text)
        return
    if backend != "smtp":
        raise EmailSendError(f"EMAIL_BACKEND desconocido: {backend}")

    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        if s.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(s.SMTP_HOST, s.SMTP_PORT, timeout=15, context=ssl.create_default_context()) as smtp:
                if s.SMTP_USER:
                    smtp.login(s.SMTP_USER, s.SMTP_PASSWORD or "")
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as smtp:
                if s.SMTP_USE_TLS:
                    smtp.starttls(context=ssl.create_default_context())
                if s.SMTP_USER:
                    smtp.login(s.SMTP_USER, s.SMTP_PASSWORD or "")
                smtp.send_message(msg)
    except Exception as e:  # no se filtra el detalle al cliente; queda en el log
        logger.error("Falló el envío SMTP a %s: %s", to, e)
        raise EmailSendError("No se pudo enviar el correo") from e


def send_password_reset_code(to: str, name: str | None, code: str, minutes: int, support_email: str | None) -> None:
    saludo = f"Hola {name.split()[0]}," if name and name.strip() else "Hola,"
    soporte = f"\nSi necesitas ayuda, escríbenos a {support_email}." if support_email else ""
    text = (
        f"{saludo}\n\n"
        f"Tu código para restablecer la contraseña de PROXVEL es:\n\n"
        f"    {code}\n\n"
        f"Vence en {minutes} minutos y solo sirve una vez.\n"
        f"Si no lo pediste tú, ignora este mensaje: tu contraseña no cambió.{soporte}\n\n"
        f"— Equipo PROXVEL"
    )
    send_email(to, "Tu código para restablecer la contraseña de PROXVEL", text)
