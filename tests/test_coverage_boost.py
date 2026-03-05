import pytest
from decimal import Decimal


class TestValidators:
    def test_rwanda_phone_valid_mtn(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+250788123456')
        assert is_valid is True
        assert error is None

    def test_rwanda_phone_valid_airtel(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+250722123456')
        assert is_valid is True

    def test_rwanda_phone_invalid_prefix(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+254788123456')
        assert is_valid is False
        assert 'must start with +250' in error

    def test_rwanda_phone_invalid_length(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+25078812345')
        assert is_valid is False

    def test_rwanda_phone_invalid_network(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+250799123456')
        assert is_valid is False

    def test_rwanda_phone_with_spaces(self):
        from core.validators import validate_rwanda_phone
        is_valid, error = validate_rwanda_phone('+250 788 123 456')
        assert is_valid is True

    def test_rwanda_nid_valid(self):
        from core.validators import validate_rwanda_nid
        is_valid, error = validate_rwanda_nid('1199870123456789')
        assert is_valid is True

    def test_rwanda_nid_invalid_length(self):
        from core.validators import validate_rwanda_nid
        is_valid, error = validate_rwanda_nid('119987012345')
        assert is_valid is False
        assert '16 digits' in error

    def test_rwanda_nid_invalid_prefix(self):
        from core.validators import validate_rwanda_nid
        is_valid, error = validate_rwanda_nid('2199870123456789')
        assert is_valid is False
        assert 'start with 1' in error

    def test_rwanda_nid_invalid_year(self):
        from core.validators import validate_rwanda_nid
        is_valid, error = validate_rwanda_nid('1189970123456789')
        assert is_valid is False
        assert 'birth year' in error.lower()

    def test_rwanda_tin_valid(self):
        from core.validators import validate_tin
        is_valid, error = validate_tin('123456789')
        assert is_valid is True

    def test_rwanda_tin_invalid_length(self):
        from core.validators import validate_tin
        is_valid, error = validate_tin('12345')
        assert is_valid is False
        assert '9 digits' in error

    def test_rwanda_tin_non_numeric(self):
        from core.validators import validate_tin
        is_valid, error = validate_tin('12345678A')
        assert is_valid is False

    def test_passport_valid_short(self):
        from core.validators import validate_passport
        is_valid, error = validate_passport('AB1234')
        assert is_valid is True

    def test_passport_valid_long(self):
        from core.validators import validate_passport
        is_valid, error = validate_passport('AB1234567')
        assert is_valid is True

    def test_passport_invalid_length(self):
        from core.validators import validate_passport
        is_valid, error = validate_passport('AB12')
        assert is_valid is False
        assert '6-9 characters' in error

    def test_passport_invalid_chars(self):
        from core.validators import validate_passport
        is_valid, error = validate_passport('AB@1234')
        assert is_valid is False


class TestEncryption:
    def test_encrypt_decrypt_nid(self):
        from core.encryption import EncryptedCharField
        field = EncryptedCharField()
        
        original = '1199870123456789'
        encrypted = field.get_prep_value(original)
        decrypted = field.from_db_value(encrypted, None, None)
        
        assert encrypted != original
        assert decrypted == original

    def test_encrypt_none(self):
        from core.encryption import EncryptedCharField
        field = EncryptedCharField()
        result = field.get_prep_value(None)
        assert result is None

    def test_decrypt_none(self):
        from core.encryption import EncryptedCharField
        field = EncryptedCharField()
        result = field.from_db_value(None, None, None)
        assert result is None

    def test_decrypt_empty_string(self):
        from core.encryption import EncryptedCharField
        field = EncryptedCharField()
        result = field.from_db_value('', None, None)
        assert result == ''


@pytest.mark.django_db
class TestPricing:
    def test_calculate_shipping_cost_zone1(self):
        from core.pricing import calculate_shipping_cost
        from core.models import ShippingZone
        
        ShippingZone.objects.get_or_create(
            code='ZONE_1',
            defaults={
                'name': 'Kigali',
                'base_rate': Decimal('1500'),
                'per_kg_rate': Decimal('200')
            }
        )
        
        result = calculate_shipping_cost('Kigali', Decimal('5.0'))
        assert result['zone'] == 'ZONE_1'
        assert result['total_cost'] == Decimal('2500')

    def test_calculate_shipping_cost_zone2(self):
        from core.pricing import calculate_shipping_cost
        from core.models import ShippingZone
        
        ShippingZone.objects.get_or_create(
            code='ZONE_2',
            defaults={
                'name': 'Provinces',
                'base_rate': Decimal('3000'),
                'per_kg_rate': Decimal('300')
            }
        )
        
        result = calculate_shipping_cost('Huye', Decimal('10.0'))
        assert result['zone'] == 'ZONE_2'


@pytest.mark.django_db
class TestModels:
    def test_user_creation(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            phone='+250788123456',
            password='testpass123',
            user_type='CUSTOMER'
        )
        assert user.phone == '+250788123456'
        assert user.user_type == 'CUSTOMER'

    def test_shipping_zone_str(self):
        from core.models import ShippingZone
        
        zone = ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200')
        )
        assert str(zone) == 'ZONE_1 - Kigali'

    def test_domestic_shipment_tracking_number(self):
        from domestic.models import DomesticShipment
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        
        shipment = DomesticShipment.objects.create(
            customer=user,
            origin='Kigali',
            destination='Huye',
            weight_kg=Decimal('5.0'),
            description='Test',
            recipient_phone='+250788999999',
            recipient_name='Recipient',
            cost=Decimal('5000')
        )
        assert shipment.tracking_number.startswith('RW-D-')
