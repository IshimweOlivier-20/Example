import pytest
from core.validators import validate_rwanda_phone, validate_rwanda_nid, validate_tin, validate_passport


class TestValidatorsComplete:
    def test_phone_mtn_valid(self):
        assert validate_rwanda_phone('+250788123456')[0] is True
        assert validate_rwanda_phone('+250789123456')[0] is True
        assert validate_rwanda_phone('+250738123456')[0] is True
    
    def test_phone_airtel_valid(self):
        assert validate_rwanda_phone('+250722123456')[0] is True
        assert validate_rwanda_phone('+250723123456')[0] is True
    
    def test_phone_invalid_prefix(self):
        is_valid, error = validate_rwanda_phone('+254788123456')
        assert is_valid is False
        assert '+250' in error
    
    def test_phone_invalid_length_short(self):
        is_valid, error = validate_rwanda_phone('+25078812345')
        assert is_valid is False
    
    def test_phone_invalid_length_long(self):
        is_valid, error = validate_rwanda_phone('+2507881234567')
        assert is_valid is False
    
    def test_phone_invalid_network(self):
        is_valid, error = validate_rwanda_phone('+250799123456')
        assert is_valid is False
    
    def test_phone_with_spaces(self):
        assert validate_rwanda_phone('+250 788 123 456')[0] is True
    
    def test_phone_with_dashes(self):
        assert validate_rwanda_phone('+250-788-123-456')[0] is True
    
    def test_nid_valid_1990s(self):
        assert validate_rwanda_nid('1199070123456789')[0] is True
        assert validate_rwanda_nid('1199570123456789')[0] is True
    
    def test_nid_valid_1980s(self):
        assert validate_rwanda_nid('1198070123456789')[0] is True
        assert validate_rwanda_nid('1198570123456789')[0] is True
    
    def test_nid_valid_2000s(self):
        assert validate_rwanda_nid('1200070123456789')[0] is True
        assert validate_rwanda_nid('1200570123456789')[0] is True
    
    def test_nid_invalid_length(self):
        is_valid, error = validate_rwanda_nid('119987012345')
        assert is_valid is False
        assert '16 digits' in error
    
    def test_nid_invalid_prefix(self):
        is_valid, error = validate_rwanda_nid('2199870123456789')
        assert is_valid is False
        assert 'start with 1' in error
    
    def test_nid_invalid_year_too_old(self):
        is_valid, error = validate_rwanda_nid('1189970123456789')
        assert is_valid is False
    
    def test_nid_invalid_year_future(self):
        is_valid, error = validate_rwanda_nid('1230070123456789')
        assert is_valid is False
    
    def test_nid_non_numeric(self):
        is_valid, error = validate_rwanda_nid('119987012345678A')
        assert is_valid is False
    
    def test_tin_valid_9_digits(self):
        assert validate_tin('123456789')[0] is True
        assert validate_tin('100000000')[0] is True
        assert validate_tin('999999999')[0] is True
    
    def test_tin_invalid_length_short(self):
        is_valid, error = validate_tin('12345')
        assert is_valid is False
        assert '9 digits' in error
    
    def test_tin_invalid_length_long(self):
        is_valid, error = validate_tin('1234567890')
        assert is_valid is False
    
    def test_tin_non_numeric(self):
        is_valid, error = validate_tin('12345678A')
        assert is_valid is False
    
    def test_tin_with_spaces(self):
        # TIN should not have spaces
        is_valid, error = validate_tin('123456789')
        assert is_valid is True
    
    def test_passport_valid_6_chars(self):
        assert validate_passport('AB1234')[0] is True
    
    def test_passport_valid_7_chars(self):
        assert validate_passport('AB12345')[0] is True
    
    def test_passport_valid_8_chars(self):
        assert validate_passport('AB123456')[0] is True
    
    def test_passport_valid_9_chars(self):
        assert validate_passport('AB1234567')[0] is True
    
    def test_passport_invalid_too_short(self):
        is_valid, error = validate_passport('AB12')
        assert is_valid is False
        assert '6-9 characters' in error
    
    def test_passport_invalid_too_long(self):
        is_valid, error = validate_passport('AB12345678')
        assert is_valid is False
    
    def test_passport_invalid_special_chars(self):
        is_valid, error = validate_passport('AB@1234')
        assert is_valid is False
    
    def test_passport_lowercase(self):
        assert validate_passport('ab1234')[0] is True
    
    def test_passport_mixed_case(self):
        assert validate_passport('Ab1234')[0] is True
