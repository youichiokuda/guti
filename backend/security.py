import os
from typing import Optional
from cryptography.fernet import Fernet

# --- Key loader ---
def _get_key() -> bytes:
    key: Optional[str] = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set")
    # Fernet expects a 32-byte urlsafe base64 key (44 chars when str)
    # Assume user sets the standard Fernet.generate_key().decode() string
    try:
        return key.encode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Invalid ENCRYPTION_KEY encoding: {e}")

def _fernet() -> Fernet:
    return Fernet(_get_key())

# --- Public API (current names) ---
def encrypt_api_token(plain: str) -> str:
    if plain is None:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")

def decrypt_api_token(cipher: str) -> str:
    if not cipher:
        return ""
    return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")

# --- Backward-compatible aliases (旧名で呼ばれても動くように) ---
def encrypt(plain: str) -> str:          # noqa: D401
    return encrypt_api_token(plain)

def decrypt(cipher: str) -> str:          # noqa: D401
    return decrypt_api_token(cipher)
