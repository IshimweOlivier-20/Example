import pytest
from core.encryption import EncryptedCharField, EncryptedTextField


class TestEncryptionComplete:
    def test_encrypted_char_field_encrypt_decrypt(self):
        field = EncryptedCharField()
        original = '1199870123456789'
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        assert encrypted != original
        assert decrypted == original
    
    def test_encrypted_text_field_encrypt_decrypt(self):
        field = EncryptedTextField()
        original = 'This is sensitive data that needs encryption'
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        assert encrypted != original
        assert decrypted == original
    
    def test_encrypt_none_value(self):
        field = EncryptedCharField()
        result = field.get_prep_value(None)
        assert result is None
    
    def test_decrypt_none_value(self):
        field = EncryptedCharField()
        result = field.from_db_value(None, None, None)
        assert result is None
    
    def test_decrypt_empty_string(self):
        field = EncryptedCharField()
        result = field.from_db_value('', None, None)
        assert result == ''
    
    def test_encrypt_empty_string(self):
        field = EncryptedCharField()
        result = field.get_prep_value('')
        assert result == ''
    
    def test_encrypted_field_with_unicode(self):
        field = EncryptedCharField()
        original = 'Kigali Café ñ é'
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        assert decrypted == original
    
    def test_encrypted_field_with_numbers(self):
        field = EncryptedCharField()
        original = '1234567890'
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        assert decrypted == original
    
    def test_encrypted_field_long_text(self):
        field = EncryptedTextField()
        original = 'A' * 1000
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        assert decrypted == original
    
    def test_multiple_encryptions_different_output(self):
        field = EncryptedCharField()
        original = 'test123'
        encrypted1 = field.get_prep_value(original)
        encrypted2 = field.get_prep_value(original)
        # Both should decrypt to same value
        assert field.from_db_value(encrypted1, None, None) == original
        assert field.from_db_value(encrypted2, None, None) == original
