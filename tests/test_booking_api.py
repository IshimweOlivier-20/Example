"""
Integration tests for booking API endpoints.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import ShippingZone

User = get_user_model()


class BookingApiTests(TestCase):
    """Integration tests for /api/shipments/create/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='testpass123',
            user_type='CUSTOMER',
            full_name='Test Customer'
        )

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

        token_response = self.client.post(
            '/api/auth/token/obtain/',
            {'phone': self.user.phone, 'password': 'testpass123'},
            format='json'
        )
        access_token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_create_domestic_booking(self):
        payload = {
            'shipment_type': 'DOMESTIC',
            'origin': 'Kigali',
            'destination': 'Kigali',
            'weight_kg': 3.5,
            'commodity_type': 'Food',
            'recipient_phone': '+250788999999',
            'recipient_name': 'Recipient A',
            'transport_type': 'MOTO'
        }

        response = self.client.post('/api/shipments/create/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('tracking_number', response.data)
        self.assertIn('payment_reference', response.data)

    def test_create_international_missing_fields(self):
        payload = {
            'shipment_type': 'INTERNATIONAL',
            'origin': 'Kigali',
            'destination': 'Nairobi',
            'weight_kg': 10,
            'commodity_type': 'Electronics',
            'recipient_phone': '+254700000000',
            'recipient_name': 'Recipient B'
        }

        response = self.client.post('/api/shipments/create/', payload, format='json')
        self.assertEqual(response.status_code, 400)
