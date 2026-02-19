"""
Encryption/decryption utility using Fernet (symmetric encryption from cryptography library).
Used to encrypt sensitive values in database (API keys, passwords, etc.).

Key management:
- ENCRYPTION_KEY is loaded from settings.ENCRYPTION_KEY environment variable
- If not set, a new key is generated and stored in .env (requires manual setup)
- Key format: base64-encoded 32-byte value as Fernet key
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption/decryption of sensitive values."""
    
    _cipher: Optional[Fernet] = None
    _key_str: Optional[str] = None
    
    @classmethod
    def _init_cipher(cls) -> None:
        """Initialize cipher on first use."""
        if cls._cipher is not None:
            return
        
        from app.core.config import settings
        
        key_str = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key_str:
            logger.warning(
                "ENCRYPTION_KEY not set in environment. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\" and set ENCRYPTION_KEY in .env"
            )
            raise ValueError(
                "ENCRYPTION_KEY not configured. Set ENCRYPTION_KEY environment variable "
                "with a Fernet key (generate with: from cryptography.fernet import Fernet; "
                "Fernet.generate_key())"
            )
        
        try:
            # Verify it's a valid Fernet key
            cls._cipher = Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
            cls._key_str = key_str
        except Exception as e:
            logger.error("Invalid ENCRYPTION_KEY format: %s", e)
            raise ValueError(f"ENCRYPTION_KEY format invalid: {e}")
    
    @classmethod
    def encrypt(cls, value: str) -> bytes:
        """
        Encrypt a string value using Fernet.
        
        Args:
            value: Plain text string to encrypt
            
        Returns:
            Encrypted bytes
            
        Raises:
            ValueError: If ENCRYPTION_KEY not configured
        """
        cls._init_cipher()
        if not cls._cipher:
            raise ValueError("Encryption not initialized")
        
        value_bytes = value.encode('utf-8') if isinstance(value, str) else value
        encrypted = cls._cipher.encrypt(value_bytes)
        return encrypted
    
    @classmethod
    def decrypt(cls, encrypted: bytes) -> str:
        """
        Decrypt an encrypted value back to string.
        
        Args:
            encrypted: Encrypted bytes (from encrypt() or stored in DB)
            
        Returns:
            Decrypted string
            
        Raises:
            ValueError: If decryption fails or ENCRYPTION_KEY not configured
        """
        cls._init_cipher()
        if not cls._cipher:
            raise ValueError("Encryption not initialized")
        
        if isinstance(encrypted, str):
            encrypted = encrypted.encode('utf-8')
        
        try:
            decrypted = cls._cipher.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except InvalidToken as e:
            logger.error("Decryption failed - invalid token or wrong key: %s", e)
            raise ValueError(f"Decryption failed: {e}")
        except Exception as e:
            logger.error("Decryption error: %s", e)
            raise ValueError(f"Decryption error: {e}")
    
    @classmethod
    def generate_key() -> str:
        """
        Generate a new Fernet key for configuration.
        Call this once and store the result in .env as ENCRYPTION_KEY.
        
        Returns:
            Base64-encoded Fernet key
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')


# Convenience functions
def encrypt_value(value: str) -> bytes:
    """Encrypt a string value."""
    return EncryptionManager.encrypt(value)


def decrypt_value(encrypted: bytes) -> str:
    """Decrypt a value."""
    return EncryptionManager.decrypt(encrypted)


def generate_encryption_key() -> str:
    """Generate a new encryption key for .env."""
    return EncryptionManager.generate_key()
