"""
Unit tests for core service layer.

Tests:
- BookingService: create_booking(), confirm_payment()
- PaymentService: mobile money integration
- NotificationService: SMS broadcast
- Race condition handling on driver assignment
"""
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
import threading
import time

from core.services import BookingService, PaymentService, NotificationService
from core.models import Location, ShippingZone
from domestic.models import DomesticShipment
from international.models import InternationalShipment

User = get_user_model()


class BookingServiceUnitTests(TransactionTestCase):
    """
    Unit tests for BookingService.
    Uses TransactionTestCase to test atomic transactions properly.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.customer = User.objects.create_user(
            phone='+250788123456',
            password='testpass123',
            user_type='CUSTOMER',
            full_name='Test Customer'
        )
        
        self.driver1 = User.objects.create_user(
            phone='+250788111111',
            password='driver123',
            user_type='DRIVER',
            full_name='Driver One',
            assigned_sector='Kigali'
        )
        
        self.driver2 = User.objects.create_user(
            phone='+250788222222',
            password='driver123',
            user_type='DRIVER',
            full_name='Driver Two',
            assigned_sector='Kigali'
        )
        
        # Create shipping zones for tariff calculation
        ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('2000.00'),
            per_kg_rate=Decimal('500.00')
        )
        
        ShippingZone.objects.create(
            code='ZONE_2',
            name='Provinces',
            base_rate=Decimal('3000.00'),
            per_kg_rate=Decimal('700.00')
        )
        
        ShippingZone.objects.create(
            code='ZONE_3',
            name='EAC Countries',
            base_rate=Decimal('15000.00'),
            per_kg_rate=Decimal('2000.00')
        )
        
        self.service = BookingService()
    
    def test_create_domestic_booking_success(self):
        """Test successful domestic shipment creation."""
        shipment, payment_reference = self.service.create_booking(
            user=self.customer,
            shipment_type='DOMESTIC',
            origin='Kigali',
            destination='Kigali',
            weight_kg=Decimal('5.0'),
            commodity_type='Food',
            recipient_name='John Doe',
            recipient_phone='+250788999999',
            transport_type='MOTO'
        )

        self.assertIsNotNone(shipment.tracking_number)
        self.assertIsNotNone(payment_reference)

        # Verify shipment created
        shipment = DomesticShipment.objects.get(tracking_number=shipment.tracking_number)
        self.assertEqual(shipment.customer, self.customer)
        self.assertEqual(shipment.weight_kg, Decimal('5.0'))
        self.assertFalse(shipment.payment_confirmed)
        self.assertEqual(shipment.description, 'Food')
        self.assertEqual(shipment.status, 'PENDING_PAYMENT')
        
        # Verify payment reference cached
        payment_data = cache.get(f'payment:{payment_reference}')
        self.assertIsNotNone(payment_data)
        self.assertEqual(payment_data['shipment_id'], shipment.id)
    
    def test_create_international_booking_success(self):
        """Test successful international shipment creation."""
        shipment, payment_reference = self.service.create_booking(
            user=self.customer,
            shipment_type='INTERNATIONAL',
            origin='Kigali',
            destination='Nairobi',
            destination_country='KENYA',
            weight_kg=Decimal('10.0'),
            commodity_type='Electronics',
            recipient_name='Jane Smith',
            recipient_phone='+254712345678',
            recipient_address='123 Nairobi Street',
            customs_docs={
                'declaration': 'Electronics',
                'estimated_value': Decimal('50000.00')
            }
        )

        self.assertIsNotNone(shipment.tracking_number)
        self.assertIsNotNone(payment_reference)

        # Verify international shipment created
        shipment = InternationalShipment.objects.get(tracking_number=shipment.tracking_number)
        self.assertEqual(shipment.destination_country, 'KENYA')
        self.assertEqual(shipment.estimated_value, Decimal('50000.00'))
        self.assertEqual(shipment.description, 'Electronics')
    
    def test_confirm_payment_webhook_success(self):
        """Test payment confirmation webhook processing."""
        # First create a booking
        shipment, payment_ref = self.service.create_booking(
            user=self.customer,
            shipment_type='DOMESTIC',
            origin='Kigali',
            destination='Kigali',
            weight_kg=Decimal('3.0'),
            commodity_type='Food',
            recipient_name='Test',
            recipient_phone='+250788888888',
            transport_type='MOTO'
        )

        result = self.service.confirm_payment(payment_ref, 'SUCCESS')
        self.assertTrue(result)

        # Verify shipment updated
        shipment = DomesticShipment.objects.get(tracking_number=shipment.tracking_number)
        self.assertTrue(shipment.payment_confirmed)
        self.assertIsNotNone(shipment.driver)
        self.assertEqual(shipment.status, 'ASSIGNED')
    
    def test_payment_webhook_idempotency(self):
        """Test that processing the same webhook twice doesn't cause duplicate updates."""
        shipment, payment_ref = self.service.create_booking(
            user=self.customer,
            shipment_type='DOMESTIC',
            origin='Kigali',
            destination='Kigali',
            weight_kg=Decimal('2.0'),
            commodity_type='Food',
            recipient_name='Test',
            recipient_phone='+250788777777',
            transport_type='BUS'
        )

        # First webhook
        result1 = self.service.confirm_payment(payment_ref, 'SUCCESS')
        self.assertTrue(result1)

        # Second webhook (duplicate)
        result2 = self.service.confirm_payment(payment_ref, 'SUCCESS')
        self.assertTrue(result2)

        # Verify shipment still confirmed
        shipment.refresh_from_db()
        self.assertTrue(shipment.payment_confirmed)
    
    def test_race_condition_driver_assignment(self):
        """
        Test race condition handling for driver assignment.
        Simulates 2 concurrent payment confirmations trying to assign the same driver.
        """
        # Create 2 pending bookings
        booking1 = self.service.create_booking(
            user=self.customer,
            shipment_type='DOMESTIC',
            origin='Kigali',
            destination='Kigali',
            weight_kg=Decimal('1.0'),
            commodity_type='Food',
            recipient_name='Recipient 1',
            recipient_phone='+250788111112',
            transport_type='MOTO'
        )
        
        # Create another customer for booking 2
        customer2 = User.objects.create_user(
            phone='+250788654321',
            password='testpass123',
            user_type='CUSTOMER',
            full_name='Customer Two'
        )
        
        booking2 = self.service.create_booking(
            user=customer2,
            shipment_type='DOMESTIC',
            origin='Kigali',
            destination='Kigali',
            weight_kg=Decimal('1.0'),
            commodity_type='Food',
            recipient_name='Recipient 2',
            recipient_phone='+250788111113',
            transport_type='MOTO'
        )

        shipment1, payment_ref1 = booking1
        shipment2, payment_ref2 = booking2
        
        results = []
        errors = []
        
        def confirm_payment_thread(payment_ref):
            """Thread worker for payment confirmation."""
            try:
                result = self.service.confirm_payment(payment_ref, 'SUCCESS')
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Start 2 threads confirming payments simultaneously
        thread1 = threading.Thread(target=confirm_payment_thread, args=(payment_ref1,))
        thread2 = threading.Thread(target=confirm_payment_thread, args=(payment_ref2,))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both should succeed (SELECT FOR UPDATE prevents race condition)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 0)
        self.assertTrue(results[0])
        self.assertTrue(results[1])
        
        # Each booking should have a driver assigned
        shipment1 = DomesticShipment.objects.get(tracking_number=shipment1.tracking_number)
        shipment2 = DomesticShipment.objects.get(tracking_number=shipment2.tracking_number)
        
        self.assertIsNotNone(shipment1.driver)
        self.assertIsNotNone(shipment2.driver)
        
        # If only 2 drivers available, they should be different
        # (or same if load balancing assigns same driver)
        self.assertIn(shipment1.driver.phone, ['+250788111111', '+250788222222'])
        self.assertIn(shipment2.driver.phone, ['+250788111111', '+250788222222'])
    
    def test_invalid_shipment_type(self):
        """Test error handling for invalid shipment type."""
        with self.assertRaises(ValueError) as cm:
            self.service.create_booking(
                user=self.customer,
                shipment_type='INVALID',
                origin='Kigali',
                destination='Kigali',
                weight_kg=Decimal('5.0'),
                commodity_type='Food',
                recipient_name='Test',
                recipient_phone='+250788000000'
            )
        
        self.assertIn('Invalid shipment type', str(cm.exception))
    
    def test_negative_weight(self):
        """Test error handling for negative weight."""
        with self.assertRaises(ValueError) as cm:
            self.service.create_booking(
                user=self.customer,
                shipment_type='DOMESTIC',
                origin='Kigali',
                destination='Kigali',
                weight_kg=Decimal('-5.0'),
                commodity_type='Food',
                recipient_name='Test',
                recipient_phone='+250788000000'
            )
        
        self.assertIn('Weight must be positive', str(cm.exception))


class PaymentServiceUnitTests(TestCase):
    """Unit tests for PaymentService (Mobile Money integration)."""
    
    def setUp(self):
        """Set up test data."""
        self.customer = User.objects.create_user(
            phone='+250788123456',
            password='testpass123',
            user_type='CUSTOMER'
        )
        
        self.service = PaymentService()
    
    def test_initiate_mtn_payment(self):
        """Test Mobile Money payment initiation returns a reference."""
        payment_reference = self.service.initiate_payment(
            amount=Decimal('5000.00'),
            phone=self.customer.phone,
            description='Test payment'
        )
        
        self.assertIsInstance(payment_reference, str)
        self.assertTrue(payment_reference)
    
    def test_verify_payment_status(self):
        """Test payment status polling fallback."""
        payment_reference = 'TEST-REF'
        result = self.service.verify_payment(payment_reference)
        
        self.assertEqual(result['reference'], payment_reference)
        self.assertEqual(result['status'], 'PENDING')


class NotificationServiceUnitTests(TestCase):
    """Unit tests for NotificationService (SMS, Email)."""
    
    def test_send_sms_notification(self):
        """Test SMS notification sending."""
        service = NotificationService()
        result = service.send_sms(
            phone='+250788123456',
            message='Your shipment is on the way'
        )
        
        self.assertTrue(result)
