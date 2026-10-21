"""
PROXVEL Backend - Límite de intentos (en memoria).

Ventana deslizante por clave (cada limiter se usa siempre con la misma ventana). Suficiente para una instancia única de uvicorn
(el despliegue previsto). Si se corre con varios workers/instancias, cada uno
lleva su propio contador y el límite efectivo se multiplica; en ese caso hay que
mover el contador a Redis o a la base de datos.
"""
import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.config.settings import get_settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_purge = time.monotonic()

    def _prune(self, key: str, window: float, now: float) -> deque[float]:
        q = self._hits.get(key)
        if q is None:
            return deque()
        while q and now - q[0] >= window:
            q.popleft()
        if not q:
            self._hits.pop(key, None)
            return deque()
        return q

    def _purge_all(self, window: float, now: float) -> None:
        """Evita que el diccionario crezca sin límite con claves viejas."""
        if now - self._last_purge < 60:
            return
        self._last_purge = now
        for key in list(self._hits):
            self._prune(key, window, now)

    def count(self, key: str, window: float) -> int:
        now = time.monotonic()
        with self._lock:
            self._purge_all(window, now)
            return len(self._prune(key, window, now))

    def retry_after(self, key: str, window: float) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, window, now)
            return max(1, int(window - (now - q[0]))) if q else 0

    def hit(self, key: str, window: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._purge_all(window, now)
            q = self._prune(key, window, now)
            q.append(now)
            self._hits[key] = q

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Contadores globales
login_failures = SlidingWindowLimiter()
register_attempts = SlidingWindowLimiter()
forgot_attempts = SlidingWindowLimiter()   # solicitudes de código (ventana de 1 h)
reset_attempts = SlidingWindowLimiter()    # intentos de canjear un código (ventana de 1 h)
announcement_events = SlidingWindowLimiter()  # vistas/clics de anuncios reportados por la app (ventana de 1 min)


def client_ip(request: Request) -> str:
    """IP del cliente. Solo confía en X-Forwarded-For si TRUST_PROXY_HEADERS está activo."""
    if get_settings().TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many(seconds: int) -> HTTPException:
    minutes = max(1, -(-seconds // 60))
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Demasiados intentos. Intenta de nuevo en {minutes} minuto{'s' if minutes != 1 else ''}.",
        headers={"Retry-After": str(seconds)},
    )


def _login_keys(ip: str, email: str) -> tuple[str, str]:
    return f"login:{ip}:{email.strip().lower()}", f"login-ip:{ip}"


def enforce_login_allowed(request: Request, email: str) -> None:
    """Lanza 429 si esa IP+correo, o esa IP en general, acumuló demasiados fallos."""
    s = get_settings()
    pair_key, ip_key = _login_keys(client_ip(request), email)
    w = s.LOGIN_WINDOW_SECONDS
    if login_failures.count(pair_key, w) >= s.LOGIN_MAX_FAILURES:
        raise _too_many(login_failures.retry_after(pair_key, w))
    if login_failures.count(ip_key, w) >= s.LOGIN_MAX_FAILURES_PER_IP:
        raise _too_many(login_failures.retry_after(ip_key, w))


def record_login_failure(request: Request, email: str) -> None:
    w = get_settings().LOGIN_WINDOW_SECONDS
    pair_key, ip_key = _login_keys(client_ip(request), email)
    login_failures.hit(pair_key, w)
    login_failures.hit(ip_key, w)


def record_login_success(request: Request, email: str) -> None:
    pair_key, _ = _login_keys(client_ip(request), email)
    login_failures.clear(pair_key)


def enforce_register_allowed(request: Request) -> None:  # usado como dependencia de la ruta
    """Cuenta cada intento de registro por IP (1 hora)."""
    s = get_settings()
    key = f"register:{client_ip(request)}"
    window = 3600
    if register_attempts.count(key, window) >= s.REGISTER_MAX_PER_IP:
        raise _too_many(register_attempts.retry_after(key, window))
    register_attempts.hit(key, window)


def enforce_forgot_allowed(request: Request, email: str) -> None:
    """Limita las solicitudes de código por IP y por correo (cuenta cada intento, exista o no la cuenta)."""
    s = get_settings()
    ip = client_ip(request)
    window = 3600
    for key, limit in ((f"forgot-ip:{ip}", s.PASSWORD_RESET_PER_IP),
                       (f"forgot-email:{email.strip().lower()}", s.PASSWORD_RESET_PER_EMAIL)):
        if forgot_attempts.count(key, window) >= limit:
            raise _too_many(forgot_attempts.retry_after(key, window))
    forgot_attempts.hit(f"forgot-ip:{ip}", window)
    forgot_attempts.hit(f"forgot-email:{email.strip().lower()}", window)


def enforce_reset_allowed(request: Request, email: str) -> None:
    """Frena la adivinación de códigos repartida entre correos (por IP) o sobre un mismo correo."""
    ip = client_ip(request)
    window = 3600
    for key, limit in ((f"reset-ip:{ip}", 20), (f"reset-email:{email.strip().lower()}", 10)):
        if reset_attempts.count(key, window) >= limit:
            raise _too_many(reset_attempts.retry_after(key, window))
    reset_attempts.hit(f"reset-ip:{ip}", window)
    reset_attempts.hit(f"reset-email:{email.strip().lower()}", window)
