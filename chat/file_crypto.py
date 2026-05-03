import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Load or generate a persistent encryption key
KEY_FILE = ".file_encryption_key"

def get_encryption_key() -> bytes:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = AESGCM.generate_key(bit_length=256)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def encrypt_file(data: bytes) -> str:
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, data, None)
    # Store nonce + encrypted data together, base64 encoded
    combined = nonce + encrypted
    return base64.b64encode(combined).decode()

def decrypt_file(encrypted_b64: str) -> bytes:
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    combined = base64.b64decode(encrypted_b64.encode())
    nonce = combined[:12]
    encrypted = combined[12:]
    return aesgcm.decrypt(nonce, encrypted, None)