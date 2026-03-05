import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.core.cache import cache

from core.services import BookingService, PaymentService, NotificationService

User = get_user_model()

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()

@pytest.mark.django_db
class TestBookingService:
    def setup_method(self):
        self.customer, _ = User.objects.get_or_create(
            phone="+250780000001", 
            defaults={'password': 'pass123', 'full_name': 'Test Customer'}
        )
        User.objects.get_or_create(
            phone="+250780000002", 
            defaults={'user_type': 'DRIVER', 'is_active': True}
        )
        self.mock_payment = MagicMock(spec=PaymentService)
        self.mock_notify = MagicMock(spec=NotificationService)
        self.service = BookingService(
            payment_service=self.mock_payment, 
            notification_service=self.mock_notify
        )

    @patch('core.services.calculate_shipping_cost')
    def test_create_domestic_booking(self, mock_calc):
        mock_calc.return_value = {'total_cost': 2500, 'zone': 'ZONE_2'}
        self.mock_payment.initiate_payment.return_value = "pay_ref_001"
        
        shipment, ref = self.service.create_booking(
            user=self.customer, shipment_type='DOMESTIC', origin='Kigali',
            destination='Musanze', weight_kg=Decimal('10.0'), commodity_type='Potatoes',
            recipient_phone='+250781234567', recipient_name='Jean'
        )
        
        assert shipment.status == 'PENDING_PAYMENT'
        assert shipment.cost == Decimal('2500')
        assert ref == "pay_ref_001"

    @patch('core.services.calculate_shipping_cost')
    def test_create_international_booking(self, mock_calc):
        mock_calc.return_value = {'total_cost': 15000, 'zone': 'ZONE_3'}
        self.mock_payment.initiate_payment.return_value = "pay_ref_002"
        
        shipment, ref = self.service.create_booking(
            user=self.customer, shipment_type='INTERNATIONAL', origin='Kigali',
            destination='Kampala', destination_country='UG', weight_kg=Decimal('20.0'),
            commodity_type='Coffee', recipient_phone='+256700000000',
            recipient_name='Uganda Buyer', recipient_address='Kampala Road',
            customs_docs={'declaration': 'Coffee beans', 'estimated_value': 50000}
        )
        
        assert shipment.status == 'PENDING_PAYMENT'
        assert ref == "pay_ref_002"

    @patch('core.services.calculate_shipping_cost')
    def test_invalid_shipment_type(self, mock_calc):
        with pytest.raises(ValueError, match="Invalid shipment type"):
            self.service.create_booking(
                user=self.customer, shipment_type='INVALID', origin='Kigali',
                destination='Musanze', weight_kg=Decimal('5'), commodity_type='Art',
                recipient_phone='+250780000000', recipient_name='Recipient'
            )

    @patch('core.services.calculate_shipping_cost')
    def test_negative_weight(self, mock_calc):
        with pytest.raises(ValueError, match="Weight must be positive"):
            self.service.create_booking(
                user=self.customer, shipment_type='DOMESTIC', origin='Kigali',
                destination='Musanze', weight_kg=Decimal('-5'), commodity_type='Art',
                recipient_phone='+250780000000', recipient_name='Recipient'
            )

    @patch('core.services.calculate_shipping_cost')
    def test_international_missing_country(self, mock_calc):
        with pytest.raises(ValueError, match="Destination country and recipient address are required"):
            self.service.create_booking(
                user=self.customer, shipment_type='INTERNATIONAL', origin='Kigali',
                destination='Kampala', weight_kg=Decimal('10'), commodity_type='Coffee',
                recipient_phone='+256700000000', recipient_name='Buyer'
            )

    @patch('core.services.calculate_shipping_cost')
    def test_international_missing_customs(self, mock_calc):
        with pytest.raises(ValueError, match="Customs documentation is required"):
            self.service.create_booking(
                user=self.customer, shipment_type='INTERNATIONAL', origin='Kigali',
                destination='Kampala', destination_country='UG', weight_kg=Decimal('10'),
                commodity_type='Coffee', recipient_phone='+256700000000',
                recipient_name='Buyer', recipient_address='Kampala'
            )

    @patch('core.services.calculate_shipping_cost')
    def test_confirm_payment_success(self, mock_calc):
        mock_calc.return_value = {'total_cost': 2500, 'zone': 'ZONE_2'}
        self.mock_payment.initiate_payment.return_value = "ref_abc"
        
        shipment, ref = self.service.create_booking(
            user=self.customer, shipment_type='DOMESTIC', origin='Kigali',
            destination='Musanze', weight_kg=Decimal('5'), commodity_type='Art',
            recipient_phone='+250780000000', recipient_name='Recipient'
        )
        
        success = self.service.confirm_payment(ref, "SUCCESS")
        shipment.refresh_from_db()
        
        assert success is True
        assert shipment.status == 'ASSIGNED'
        assert shipment.payment_confirmed is True
        assert shipment.driver is not None

    @patch('core.services.calculate_shipping_cost')
    def test_confirm_payment_failure(self, mock_calc):
        mock_calc.return_value = {'total_cost': 2500, 'zone': 'ZONE_2'}
        shipment, ref = self.service.create_booking(
            user=self.customer, shipment_type='DOMESTIC', origin='Kigali',
            destination='Musanze', weight_kg=Decimal('5'), commodity_type='Art',
            recipient_phone='+250780000000', recipient_name='Recipient'
        )
        
        success = self.service.confirm_payment(ref, "FAILED")
        shipment.refresh_from_db()
        
        assert success is True
        assert shipment.status == 'PAYMENT_FAILED'
        assert shipment.payment_confirmed is False

    def test_confirm_payment_not_found(self):
        success = self.service.confirm_payment("nonexistent_ref", "SUCCESS")
        assert success is False

    def test_confirm_payment_already_processed(self):
        cache.set('payment:processed:ref_123', {'status': 'SUCCESS'}, timeout=3600)
        success = self.service.confirm_payment("ref_123", "SUCCESS")
        assert success is True


@pytest.mark.django_db
class TestPaymentService:
    def test_initiate_payment(self):
        service = PaymentService()
        ref = service.initiate_payment(
            amount=Decimal('5000'),
            phone='+250788123456',
            description='Test payment'
        )
        assert ref is not None
        assert len(ref) > 0

    def test_verify_payment(self):
        service = PaymentService()
        result = service.verify_payment('test_ref')
        assert 'reference' in result
        assert 'status' in result


@pytest.mark.django_db
class TestNotificationService:
    def test_send_sms(self):
        service = NotificationService()
        result = service.send_sms('+250788123456', 'Test message')
        assert result is True

    def test_send_email(self):
        service = NotificationService()
        result = service.send_email('test@example.com', 'Subject', 'Body')
        assert result is True

    def test_broadcast_alert(self):
        User.objects.create(
            phone='+250788111111',
            user_type='DRIVER',
            is_active=True
        )
        service = NotificationService()
        count = service.broadcast_alert('DRIVER', 'Emergency alert')
        assert count >= 1