import os
from cryptography.fernet import Fernet, InvalidToken

def _get_key() -> bytes:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set")
    # Expect a Fernet key (urlsafe base64-encoded 32 bytes).
    # If user provided raw base64 32 bytes, it's already suitable.
    try:
        Fernet(key)  # validate
        return key.encode() if isinstance(key, str) else key
    except Exception:
        # Try to coerce if they passed plain bytes base64
        k = key.encode() if isinstance(key, str) else key
        return k

def encrypt(plaintext: str) -> str:
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()

def decrypt(token: str) -> str:
    f = Fernet(_get_key())
    return f.decrypt(token.encode()).decode()
