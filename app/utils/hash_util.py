import hashlib
import os

# MVP Hash Utility using standard library (hashlib).
# TODO: Replace with passlib (bcrypt) in Phase 3D (Auth Real).

ITERATIONS = 100000

def get_password_hash(password: str) -> str:
    """Hashea un password usando pbkdf2_hmac con un salt aleatorio por usuario para MVP."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    # Formato: pbkdf2_sha256$iterations$salt_hex$hash_hex
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si el password en texto plano coincide con el hash combinado."""
    if hashed_password == "demo_not_for_auth":
        return False
        
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
