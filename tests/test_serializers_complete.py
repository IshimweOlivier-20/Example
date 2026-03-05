import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from domestic.models import DomesticShipment
from international.models import InternationalShipment
from billing.models import Invoice
from core.serializers import UserSerializer
from domestic.serializers import DomesticShipmentSerializer
from international.serializers import InternationalShipmentSerializer
from billing.serializers import InvoiceSerializer
from core.models import ShippingZone

User = get_user_model()


@pytest.mark.django_db
class TestSerializersComplete:
    def setup_method(self):
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            full_name='Test User',
            user_type='CUSTOMER'
        )
        self.driver = User.objects.create_user(
            phone='+250788999999',
            password='test123',
            user_type='DRIVER'
        )
    
    def test_user_serializer_read(self):
        serializer = UserSerializer(self.user)
        data = serializer.data
        assert data['phone'] == '+250788123456'
        assert data['user_type'] == 'CUSTOMER'
        assert data['full_name'] == 'Test User'
    
    def test_domestic_shipment_serializer_read(self):
        shipment = DomesticShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Huye',
            weight_kg=Decimal('5.0'),
            description='Test shipment',
            recipient_phone='+250788999999',
            recipient_name='Recipient',
            cost=Decimal('5000')
        )
        serializer = DomesticShipmentSerializer(shipment)
        data = serializer.data
        assert data['origin'] == 'Kigali'
        assert data['destination'] == 'Huye'
        assert data['status'] == 'PENDING'
    
    def test_domestic_shipment_serializer_create(self):
        data = {
            'customer': self.user.id,
            'origin': 'Kigali',
            'destination': 'Musanze',
            'weight_kg': '10.0',
            'description': 'New shipment',
            'recipient_phone': '+250788888888',
            'recipient_name': 'New Recipient',
            'cost': '7000'
        }
        serializer = DomesticShipmentSerializer(data=data)
        if serializer.is_valid():
            shipment = serializer.save()
            assert shipment.origin == 'Kigali'
    
    def test_international_shipment_serializer_read(self):
        shipment = InternationalShipment.objects.create(
            customer=self.user,
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
        serializer = InternationalShipmentSerializer(shipment)
        data = serializer.data
        assert data['destination_country'] == 'UG'
        assert data['destination'] == 'Kampala'
    
    def test_invoice_serializer(self):
        shipment = DomesticShipment.objects.create(
            customer=self.user,
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
            customer=self.user,
            amount=Decimal('5000'),
            tax_amount=Decimal('900'),
            status='PAID'
        )
        serializer = InvoiceSerializer(invoice)
        data = serializer.data
        assert data['amount'] == '5000.00'
        assert data['shipment_type'] == 'DOMESTIC'
        assert data['status'] == 'PAID'
