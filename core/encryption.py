"""
Encrypted field implementations for sensitive data storage.
Uses Fernet symmetric encryption to encrypt data at rest.

Compliance: Data Protection and Privacy Law N° 058/2021 (Article 22)
- Sensitive personal data must be encrypted in the database
- Encryption key must be stored securely (environment variables)
"""
from typing import Any, Optional
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64


def get_encryption_key() -> bytes:
    """
    Retrieve or generate encryption key from settings.
    
    Returns:
        Fernet-compatible encryption key
        
    Note:
        In production, this MUST be stored in environment variables,
        not hardcoded. The key should be generated once and reused.
    """
    key_string = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    
    if not key_string:
        # Development fallback - DO NOT use in production
        # Generate a key if none exists (this is for development only)
        import os
        key_string = os.environ.get('FIELD_ENCRYPTION_KEY')
        
        if not key_string:
            # Last resort: generate a temporary key
            # WARNING: This will change on restart, making old data unreadable
            return Fernet.generate_key()
    
    # Ensure key is bytes
    if isinstance(key_string, str):
        key_string = key_string.encode('utf-8')
    
    return key_string


class EncryptedCharField(models.CharField):
    """
    CharField that automatically encrypts data before storing in database.
    Decrypts transparently when accessed.
    
    Usage:
        nid_number = EncryptedCharField(max_length=255, blank=True)
    
    Note:
        max_length should account for encryption overhead (~40% larger)
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize encrypted field."""
        # Store original max_length for documentation
        self.original_max_length = kwargs.get('max_length', 255)
        
        # Fernet encryption adds significant overhead
        # Base64 encoding increases size by ~33%, plus Fernet metadata
        if 'max_length' in kwargs:
            # Ensure max_length can store encrypted data
            kwargs['max_length'] = max(kwargs['max_length'] * 2, 500)
        
        super().__init__(*args, **kwargs)
        
        self._fernet = None
    
    @property
    def fernet(self) -> Fernet:
        """Lazy-load Fernet instance."""
        if self._fernet is None:
            key = get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def get_prep_value(self, value: Any) -> Optional[str]:
        """
        Encrypt value before saving to database.
        
        Args:
            value: Plain text value
            
        Returns:
            Encrypted string or None
        """
        if value is None or value == '':
            return value
        
        # Ensure value is string
        if not isinstance(value, str):
            value = str(value)
        
        # Encrypt the value
        encrypted_bytes = self.fernet.encrypt(value.encode('utf-8'))
        
        # Convert to string for database storage
        return encrypted_bytes.decode('utf-8')
    
    def from_db_value(self, value: Any, expression, connection) -> Optional[str]:
        """
        Decrypt value when reading from database.
        
        Args:
            value: Encrypted database value
            expression: SQL expression (unused)
            connection: Database connection (unused)
            
        Returns:
            Decrypted plain text or None
        """
        if value is None or value == '':
            return value
        
        try:
            # Decrypt the value
            decrypted_bytes = self.fernet.decrypt(value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # If decryption fails, log and return empty string
            # This can happen if encryption key changed
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt field: {e}")
            return "[DECRYPTION_FAILED]"
    
    def to_python(self, value: Any) -> Optional[str]:
        """
        Convert value to Python string.
        
        Args:
            value: Database or form value
            
        Returns:
            Python string value
        """
        if isinstance(value, str) or value is None:
            return value
        return str(value)


class EncryptedTextField(models.TextField):
    """
    TextField that automatically encrypts data before storing in database.
    Similar to EncryptedCharField but for larger text content.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize encrypted text field."""
        super().__init__(*args, **kwargs)
        self._fernet = None
    
    @property
    def fernet(self) -> Fernet:
        """Lazy-load Fernet instance."""
        if self._fernet is None:
            key = get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def get_prep_value(self, value: Any) -> Optional[str]:
        """Encrypt value before saving to database."""
        if value is None or value == '':
            return value
        
        if not isinstance(value, str):
            value = str(value)
        
        encrypted_bytes = self.fernet.encrypt(value.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    
    def from_db_value(self, value: Any, expression, connection) -> Optional[str]:
        """Decrypt value when reading from database."""
        if value is None or value == '':
            return value
        
        try:
            decrypted_bytes = self.fernet.decrypt(value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt text field: {e}")
            return "[DECRYPTION_FAILED]"
    
    def to_python(self, value: Any) -> Optional[str]:
        """Convert value to Python string."""
        if isinstance(value, str) or value is None:
            return value
        return str(value)
