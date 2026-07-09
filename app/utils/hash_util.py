import hashlib
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ITERATIONS = 100000

def is_legacy_hash(stored_hash: str) -> bool:
    """Detecta si el hash guardado usa el formato manual antiguo de pbkdf2_sha256."""
    return stored_hash.startswith("pbkdf2_sha256$")

def password_needs_rehash(stored_hash: str) -> bool:
    """Verifica si el hash guardado necesita ser actualizado (porque es legacy o el esquema bcrypt cambió)."""
    if is_legacy_hash(stored_hash):
        return True
    try:
        return pwd_context.needs_update(stored_hash)
    except Exception:
        # En caso de que el hash sea inválido (tests con "hashed_password" o datos basura)
        return True

def get_password_hash(password: str) -> str:
    """Hashea un password usando bcrypt (esquema predeterminado nuevo)."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si el password en texto plano coincide con el hash (soporta legacy pbkdf2 o bcrypt)."""
    if hashed_password == "demo_not_for_auth":
        return False
        
    if is_legacy_hash(hashed_password):
        # Fallback para hashes antiguos (PBKDF2_SHA256 manual)
        try:
            parts = hashed_password.split('$')
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
                
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            stored_hash = parts[3]
            
            key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
            return key.hex() == stored_hash
        except Exception:
            return False
    else:
        # Usar passlib (bcrypt)
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

def make_dummy_hash_check():
    """Ejecuta una verificación vacía de passlib para mitigar Timing Attacks."""
    pwd_context.dummy_verify()
