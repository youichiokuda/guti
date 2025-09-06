import os
from cryptography.fernet import Fernet

def _get_key() -> bytes:
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set")
    # validate
    Fernet(key.encode())
    return key.encode()

def encrypt(plain: str) -> str:
    if plain is None:
        return ""
    return Fernet(_get_key()).encrypt(plain.encode()).decode()

def decrypt(token: str) -> str:
    if not token:
        return ""
    return Fernet(_get_key()).decrypt(token.encode()).decode()