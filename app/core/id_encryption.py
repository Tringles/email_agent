"""ID encryption utilities for preventing IDOR attacks."""

import hashlib
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet
from loguru import logger
from typing import Optional

from app.core.config import settings


class IDEncryption:
    """Encrypt and decrypt IDs to prevent IDOR attacks."""

    @staticmethod
    def _get_encryption_key() -> bytes:
        """Get encryption key from settings."""
        # Check if ID_ENCRYPTION_KEY is set
        id_key = getattr(settings, 'ID_ENCRYPTION_KEY', None)
        if id_key:
            # If it's already a Fernet key (base64 encoded 32 bytes), use it directly
            try:
                # Validate it's a valid Fernet key
                Fernet(id_key.encode())
                return id_key.encode()
            except Exception:
                # If not valid, derive from it
                pass
        
        # Fallback: derive from JWT_SECRET_KEY
        secret = settings.JWT_SECRET_KEY or "default-secret-key-change-in-production"
        # Use SHA256 to get consistent 32 bytes
        key_bytes = hashlib.sha256(secret.encode()).digest()
        # Fernet requires base64-encoded 32-byte key
        return urlsafe_b64encode(key_bytes)

    def __init__(self):
        """Initialize encryption."""
        try:
            key = self._get_encryption_key()
            self.cipher = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize ID encryption: {e}")
            # Fallback: generate a new key (not recommended for production)
            self.cipher = Fernet(Fernet.generate_key())
            logger.warning("Using generated encryption key. Set ID_ENCRYPTION_KEY in settings for production.")

    def encrypt_id(self, resource_type: str, id_value: int) -> str:
        """
        Encrypt an ID with resource type prefix.
        
        Args:
            resource_type: Type of resource (e.g., 'email', 'account', 'user')
            id_value: Integer ID to encrypt
            
        Returns:
            Encrypted ID string (URL-safe)
        """
        try:
            # Format: resource_type:id_value
            plaintext = f"{resource_type}:{id_value}".encode()
            encrypted = self.cipher.encrypt(plaintext)
            # Return base64 URL-safe encoded string
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt ID {id_value}: {e}")
            raise ValueError(f"Failed to encrypt ID: {e}")

    def decrypt_id(self, encrypted_id: str) -> tuple[str, int]:
        """
        Decrypt an encrypted ID.
        
        Args:
            encrypted_id: Encrypted ID string
            
        Returns:
            Tuple of (resource_type, id_value)
            
        Raises:
            ValueError: If decryption fails or format is invalid
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_id.encode())
            parts = decrypted.decode().split(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid encrypted ID format")
            resource_type, id_str = parts
            return resource_type, int(id_str)
        except Exception as e:
            logger.error(f"Failed to decrypt ID {encrypted_id}: {e}")
            raise ValueError(f"Invalid or corrupted encrypted ID: {e}")

    def encrypt_email_id(self, email_id: int) -> str:
        """Encrypt email ID."""
        return self.encrypt_id("email", email_id)

    def decrypt_email_id(self, encrypted_id: str) -> int:
        """Decrypt email ID."""
        resource_type, id_value = self.decrypt_id(encrypted_id)
        if resource_type != "email":
            raise ValueError(f"Expected email ID, got {resource_type}")
        return id_value

    def encrypt_account_id(self, account_id: int) -> str:
        """Encrypt account ID."""
        return self.encrypt_id("account", account_id)

    def decrypt_account_id(self, encrypted_id: str) -> int:
        """Decrypt account ID."""
        resource_type, id_value = self.decrypt_id(encrypted_id)
        if resource_type != "account":
            raise ValueError(f"Expected account ID, got {resource_type}")
        return id_value


# Global instance
_id_encryption: Optional[IDEncryption] = None


def get_id_encryption() -> IDEncryption:
    """Get global ID encryption instance."""
    global _id_encryption
    if _id_encryption is None:
        _id_encryption = IDEncryption()
    return _id_encryption


def encrypt_email_id(email_id: int) -> str:
    """Encrypt email ID (convenience function)."""
    return get_id_encryption().encrypt_email_id(email_id)


def decrypt_email_id(encrypted_id: str) -> int:
    """Decrypt email ID (convenience function)."""
    return get_id_encryption().decrypt_email_id(encrypted_id)


def encrypt_account_id(account_id: int) -> str:
    """Encrypt account ID (convenience function)."""
    return get_id_encryption().encrypt_account_id(account_id)


def decrypt_account_id(encrypted_id: str) -> int:
    """Decrypt account ID (convenience function)."""
    return get_id_encryption().decrypt_account_id(encrypted_id)

