"""
Tests for domestic shipment functionality.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import DomesticShipment, ShipmentLog

User = get_user_model()


class DomesticShipmentModelTest(TestCase):
    """Test domestic shipment model."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='testpass123'
        )
    
    def test_create_domestic_shipment(self):
        """Test creating a domestic shipment."""
        shipment = DomesticShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Huye',
            weight_kg=5.0,
            description='Test package',
            cost=5000,
            recipient_name='Test Recipient',
            recipient_phone='+250722456789',
            transport_type='BUS'
        )
        
        self.assertIsNotNone(shipment.tracking_number)
        self.assertTrue(shipment.tracking_number.startswith('RW-D-'))
        self.assertEqual(shipment.status, 'PENDING')
    
    def test_shipment_log_creation(self):
        """Test creating shipment logs."""
        shipment = DomesticShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Huye',
            weight_kg=5.0,
            description='Test package',
            cost=5000,
            recipient_name='Test Recipient',
            recipient_phone='+250722456789'
        )
        
        log = ShipmentLog.objects.create(
            shipment=shipment,
            status='PICKED_UP',
            location='Nyabugogo',
            notes='Package picked up from hub'
        )
        
        self.assertEqual(log.shipment, shipment)
        self.assertEqual(log.status, 'PICKED_UP')
