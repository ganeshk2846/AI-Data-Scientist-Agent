"""
backend/app/db/security.py
Symmetric encryption and decryption for database connection parameters.
Uses PBKDF2HMAC key derivation with Fernet authenticated symmetric encryption.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from backend.app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SALT_FILE = REPO_ROOT / "data" / ".security_salt"


def _get_or_create_salt() -> bytes:
    """Retrieves or generates a persistent 16-byte cryptographic salt."""
    if SALT_FILE.exists():
        try:
            salt = SALT_FILE.read_bytes()
            if len(salt) >= 16:
                return salt[:16]
        except Exception:
            pass

    SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    return salt


def _get_fernet_cipher() -> Fernet:
    """Derives a Fernet key from APP_SECRET_KEY and persistent salt."""
    salt = _get_or_create_salt()
    secret_bytes = settings.APP_SECRET_KEY.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(secret_bytes))
    return Fernet(derived_key)


def encrypt_connection_params(params: Dict[str, Any]) -> str:
    """Encrypts connection parameters dictionary into an authenticated token string."""
    cipher = _get_fernet_cipher()
    payload = json.dumps(params).encode("utf-8")
    encrypted_bytes = cipher.encrypt(payload)
    return encrypted_bytes.decode("utf-8")


def decrypt_connection_params(encrypted_token: str) -> Dict[str, Any]:
    """Decrypts token string back into connection parameters dictionary."""
    if not encrypted_token:
        return {}
    cipher = _get_fernet_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_token.encode("utf-8"))
    return json.loads(decrypted_bytes.decode("utf-8"))
