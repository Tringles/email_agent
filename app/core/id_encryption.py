"""ID encoding utilities for preventing IDOR attacks using base62."""

from loguru import logger
from typing import Optional


# Base62 alphabet: 0-9, a-z, A-Z
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _base62_encode(num: int) -> str:
    """Encode an integer to base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]
    
    encoded = []
    while num > 0:
        encoded.append(BASE62_ALPHABET[num % 62])
        num //= 62
    
    return ''.join(reversed(encoded))


def _base62_decode(encoded: str) -> int:
    """Decode a base62 string to integer."""
    num = 0
    for char in encoded:
        if char not in BASE62_ALPHABET:
            raise ValueError(f"Invalid base62 character: {char}")
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num


class IDEncryption:
    """Encode and decode IDs using base62 to prevent IDOR attacks."""

    def __init__(self):
        """Initialize encoding."""
        pass

    def encrypt_id(self, resource_type: str, id_value: int) -> str:
        """
        Encode an ID with resource type prefix using base62.
        
        Args:
            resource_type: Type of resource (e.g., 'email', 'account', 'user')
            id_value: Integer ID to encode
            
        Returns:
            Encoded ID string (base62)
        """
        try:
            # Use single character prefix for resource type
            type_prefix = {
                'email': 'e',
                'account': 'a',
                'user': 'u'
            }.get(resource_type, 'x')
            
            # Encode ID as base62
            encoded_id = _base62_encode(id_value)
            
            # Return: prefix + encoded_id
            return f"{type_prefix}{encoded_id}"
        except Exception as e:
            logger.error(f"Failed to encode ID {id_value}: {e}")
            raise ValueError(f"Failed to encode ID: {e}")

    def decrypt_id(self, encoded_id: str) -> tuple[str, int]:
        """
        Decode an encoded ID.
        
        Args:
            encoded_id: Encoded ID string (base62)
            
        Returns:
            Tuple of (resource_type, id_value)
            
        Raises:
            ValueError: If decoding fails or format is invalid
        """
        try:
            if not encoded_id or len(encoded_id) < 2:
                raise ValueError("Invalid encoded ID format")
            
            # Extract prefix and encoded value
            prefix = encoded_id[0]
            encoded_value = encoded_id[1:]
            
            # Map prefix to resource type
            type_map = {
                'e': 'email',
                'a': 'account',
                'u': 'user'
            }
            
            resource_type = type_map.get(prefix)
            if not resource_type:
                raise ValueError(f"Unknown resource type prefix: {prefix}")
            
            # Decode base62
            id_value = _base62_decode(encoded_value)
            
            return resource_type, id_value
        except Exception as e:
            logger.error(f"Failed to decode ID {encoded_id}: {e}")
            raise ValueError(f"Invalid or corrupted encoded ID: {e}")

    def encrypt_email_id(self, email_id: int) -> str:
        """Encode email ID."""
        return self.encrypt_id("email", email_id)

    def decrypt_email_id(self, encoded_id: str) -> int:
        """Decode email ID."""
        resource_type, id_value = self.decrypt_id(encoded_id)
        if resource_type != "email":
            raise ValueError(f"Expected email ID, got {resource_type}")
        return id_value

    def encrypt_account_id(self, account_id: int) -> str:
        """Encode account ID."""
        return self.encrypt_id("account", account_id)

    def decrypt_account_id(self, encoded_id: str) -> int:
        """Decode account ID."""
        resource_type, id_value = self.decrypt_id(encoded_id)
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
    """Encode email ID (convenience function)."""
    return get_id_encryption().encrypt_email_id(email_id)


def decrypt_email_id(encoded_id: str) -> int:
    """Decode email ID (convenience function)."""
    return get_id_encryption().decrypt_email_id(encoded_id)


def encrypt_account_id(account_id: int) -> str:
    """Encode account ID (convenience function)."""
    return get_id_encryption().encrypt_account_id(account_id)


def decrypt_account_id(encoded_id: str) -> int:
    """Decode account ID (convenience function)."""
    return get_id_encryption().decrypt_account_id(encoded_id)
