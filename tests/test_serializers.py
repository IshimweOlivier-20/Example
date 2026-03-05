import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from domestic.models import DomesticShipment
from domestic.serializers import DomesticShipmentSerializer
from core.serializers import UserSerializer

User = get_user_model()


@pytest.mark.django_db
class TestSerializers:
    def test_user_serializer(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            full_name='Test User',
            user_type='CUSTOMER'
        )
        serializer = UserSerializer(user)
        data = serializer.data
        assert data['phone'] == '+250788123456'
        assert data['user_type'] == 'CUSTOMER'

    def test_domestic_shipment_serializer(self):
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
        serializer = DomesticShipmentSerializer(shipment)
        data = serializer.data
        assert data['origin'] == 'Kigali'
        assert data['destination'] == 'Huye'
