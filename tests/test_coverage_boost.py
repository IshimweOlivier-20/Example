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
        from core.pricing import calculate_shipping_cost, clear_tariff_cache
        from core.models import ShippingZone
        
        clear_tariff_cache()
        ShippingZone.objects.filter(code='ZONE_1').delete()
        ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('3000'),
            per_kg_rate=Decimal('100')
        )
        
        result = calculate_shipping_cost('Kigali', Decimal('15.0'))
        assert result['zone'] == 'ZONE_1'
        assert result['total_cost'] == 4500.0

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


    def test_user_anonymize(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            full_name='John Doe',
            nid_number='1199870123456789'
        )
        user.anonymize()
        assert user.full_name == 'REDACTED'
        assert user.is_active is False

    def test_otp_is_valid(self):
        from core.models import OTPVerification
        from django.utils import timezone
        from datetime import timedelta
        
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        assert otp.is_valid() is True

    def test_audit_log_creation(self):
        from core.models import AuditLog
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123'
        )
        
        log = AuditLog.objects.create(
            user=user,
            user_phone=user.phone,
            user_type=user.user_type,
            action='VIEW',
            resource_type='shipment',
            resource_id='123',
            endpoint='/api/shipments/123/',
            request_method='GET'
        )
        assert log.action == 'VIEW'
        assert log.user == user

    def test_location_str(self):
        from core.models import Location
        
        province = Location.objects.create(
            name='Kigali',
            location_type='PROVINCE'
        )
        district = Location.objects.create(
            name='Gasabo',
            location_type='DISTRICT',
            parent=province
        )
        assert str(district) == 'Kigali/Gasabo'

    def test_international_shipment(self):
        from international.models import InternationalShipment
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123'
        )
        
        shipment = InternationalShipment.objects.create(
            customer=user,
            origin='Kigali',
            destination='Kampala',
            destination_country='UG',
            weight_kg=Decimal('10.0'),
            description='Coffee',
            recipient_phone='+256700000000',
            recipient_name='Buyer',
            recipient_address='Kampala Road',
            cost=Decimal('15000'),
            estimated_value=Decimal('50000')
        )
        assert shipment.tracking_number.startswith('RW-')
        assert shipment.destination_country == 'UG'
