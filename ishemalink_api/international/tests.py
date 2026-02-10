"""
Tests for international shipment functionality.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import InternationalShipment, CustomsDocument

User = get_user_model()


class InternationalShipmentModelTest(TestCase):
    """Test international shipment model."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='testpass123'
        )
    
    def test_create_international_shipment(self):
        """Test creating an international shipment."""
        shipment = InternationalShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Kampala',
            destination_country='UGANDA',
            weight_kg=10.0,
            description='Test package',
            cost=50000,
            estimated_value=100000,
            recipient_name='Test Recipient',
            recipient_phone='+256700123456',
            recipient_address='Kampala, Uganda',
            customs_declaration='Commercial goods'
        )
        
        self.assertIsNotNone(shipment.tracking_number)
        self.assertTrue(shipment.tracking_number.startswith('RW-UG-'))
        self.assertEqual(shipment.status, 'PENDING')
    
    def test_customs_document_creation(self):
        """Test creating customs documents."""
        shipment = InternationalShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Nairobi',
            destination_country='KENYA',
            weight_kg=10.0,
            description='Test package',
            cost=50000,
            estimated_value=100000,
            recipient_name='Test Recipient',
            recipient_phone='+254700123456',
            recipient_address='Nairobi, Kenya',
            customs_declaration='Commercial goods'
        )
        
        doc = CustomsDocument.objects.create(
            shipment=shipment,
            document_type='TIN',
            document_number='123456789',
            issuing_authority='RRA'
        )
        
        self.assertEqual(doc.shipment, shipment)
        self.assertEqual(doc.document_type, 'TIN')
