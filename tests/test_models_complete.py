import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Location,
    ShippingZone,
    AuditLog,
    OTPVerification,
    ShippingTariff
)
from domestic.models import DomesticShipment
from international.models import InternationalShipment
from billing.models import Invoice

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        assert user.phone == '+250788123456'
        assert user.check_password('test123')
    
    def test_create_superuser(self):
        user = User.objects.create_superuser(
            phone='+250788123456',
            password='test123'
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.user_type == 'ADMIN'
    
    def test_user_str(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        assert str(user) == '+250788123456 (CUSTOMER)'
    
    def test_user_anonymize(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            full_name='John Doe',
            nid_number='1199870123456789'
        )
        user.anonymize()
        assert user.full_name == 'REDACTED'
        assert user.is_active is False
        assert user.nid_number is None


@pytest.mark.django_db
class TestLocationModel:
    def test_location_str_with_parent(self):
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
    
    def test_location_str_without_parent(self):
        province = Location.objects.create(
            name='Kigali',
            location_type='PROVINCE'
        )
        assert str(province) == 'Kigali'


@pytest.mark.django_db
class TestShippingZoneModel:
    def test_shipping_zone_str(self):
        zone = ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200')
        )
        assert str(zone) == 'ZONE_1 - Kigali'


@pytest.mark.django_db
class TestAuditLogModel:
    def test_audit_log_creation(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
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
    
    def test_audit_log_str(self):
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
        assert '+250788123456' in str(log)
        assert 'VIEW' in str(log)


@pytest.mark.django_db
class TestOTPVerificationModel:
    def test_otp_is_valid_true(self):
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        assert otp.is_valid() is True
    
    def test_otp_is_valid_expired(self):
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() - timedelta(minutes=5)
        )
        assert otp.is_valid() is False
    
    def test_otp_is_valid_used(self):
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=True
        )
        assert otp.is_valid() is False
    
    def test_otp_is_valid_max_attempts(self):
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=3,
            max_attempts=3
        )
        assert otp.is_valid() is False
    
    def test_otp_str(self):
        otp = OTPVerification.objects.create(
            phone='+250788123456',
            otp_code='123456',
            purpose='LOGIN',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        assert '+250788123456' in str(otp)
        assert 'LOGIN' in str(otp)


@pytest.mark.django_db
class TestShippingTariffModel:
    def test_shipping_tariff_str(self):
        zone = ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200')
        )
        tariff = ShippingTariff.objects.create(
            name='Moto Kigali',
            transport_type='MOTO',
            zone=zone,
            min_weight_kg=Decimal('0'),
            max_weight_kg=Decimal('10'),
            base_fee=Decimal('1000'),
            per_kg_rate=Decimal('150')
        )
        assert 'MOTO' in str(tariff)
        assert 'Kigali' in str(tariff)


@pytest.mark.django_db
class TestDomesticShipmentModel:
    def test_domestic_shipment_tracking_number(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123'
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
    
    def test_domestic_shipment_str(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123'
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
        assert 'RW-D-' in str(shipment)
        assert shipment.status in str(shipment)


@pytest.mark.django_db
class TestInternationalShipmentModel:
    def test_international_shipment_tracking_number(self):
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


@pytest.mark.django_db
class TestInvoiceModel:
    def test_invoice_creation(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123'
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
        invoice = Invoice.objects.create(
            shipment_id=shipment.id,
            shipment_type='DOMESTIC',
            customer=user,
            amount=Decimal('5000'),
            tax_amount=Decimal('900'),
            status='PAID'
        )
        assert invoice.amount == Decimal('5000')
        assert invoice.status == 'PAID'
