from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from app.config.config import Config

def get_or_create_key():
    """
    Get the encryption key from environment or create a new one
    """
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        # Generate a new key if none exists
        key = Fernet.generate_key()
        # In production, this key should be stored securely and loaded from environment
        print("WARNING: Generated new encryption key. Store this securely:", key.decode())
    return key if isinstance(key, bytes) else key.encode()

def get_fernet():
    """
    Get Fernet instance for encryption/decryption
    """
    key = get_or_create_key()
    return Fernet(key)

def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data
    """
    if not data:
        return None
    f = get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data
    """
    if not encrypted_data:
        return None
    f = get_fernet()
    return f.decrypt(encrypted_data.encode()).decode()

def encrypt_dict_values(data: dict, keys_to_encrypt: list) -> dict:
    """
    Encrypt specific values in a dictionary
    """
    encrypted_data = data.copy()
    for key in keys_to_encrypt:
        if key in encrypted_data and encrypted_data[key]:
            encrypted_data[key] = encrypt_data(encrypted_data[key])
    return encrypted_data

def decrypt_dict_values(data: dict, keys_to_decrypt: list) -> dict:
    """
    Decrypt specific values in a dictionary
    """
    decrypted_data = data.copy()
    for key in keys_to_decrypt:
        if key in decrypted_data and decrypted_data[key]:
            try:
                decrypted_data[key] = decrypt_data(decrypted_data[key])
            except Exception:
                # If decryption fails, the data might not be encrypted
                pass
    return decrypted_data 