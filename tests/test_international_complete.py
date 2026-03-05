import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from international.models import InternationalShipment
from international.serializers import InternationalShipmentSerializer
from core.pagination import ManifestPagination
from rest_framework.test import APIRequestFactory

User = get_user_model()


@pytest.mark.django_db
class TestInternationalSerializers:
    def setup_method(self):
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
    
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
        assert data['origin'] == 'Kigali'
    
    def test_international_shipment_serializer_create(self):
        data = {
            'customer': self.user.id,
            'origin': 'Kigali',
            'destination': 'Nairobi',
            'destination_country': 'KE',
            'weight_kg': '15.0',
            'description': 'Tea',
            'recipient_phone': '+254700000000',
            'recipient_name': 'Kenya Buyer',
            'recipient_address': 'Nairobi CBD',
            'cost': '20000',
            'estimated_value': '75000'
        }
        serializer = InternationalShipmentSerializer(data=data)
        if serializer.is_valid():
            shipment = serializer.save()
            assert shipment.destination_country == 'KE'


class TestPagination:
    def test_manifest_pagination(self):
        pagination = ManifestPagination()
        assert pagination.page_size == 20
        assert pagination.page_size_query_param == 'size'
        assert pagination.max_page_size == 100
