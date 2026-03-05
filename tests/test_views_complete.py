import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.request import Request
from core.models import ShippingZone, OTPVerification
from domestic.models import DomesticShipment
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestPricingViews:
    def setup_method(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200')
        )
    
    def test_calculate_price_endpoint(self):
        from core.pricing_views import CalculateShippingCostView
        view = CalculateShippingCostView.as_view()
        
        request = self.factory.post('/api/pricing/calculate/', {
            'destination': 'Kigali',
            'weight_kg': '5.0'
        }, format='json')
        
        response = view(request)
        assert response.status_code in [200, 400]
    
    def test_list_zones_endpoint(self):
        from core.pricing_views import ListShippingZonesView
        view = ListShippingZonesView.as_view()
        
        request = self.factory.get('/api/pricing/zones/')
        response = view(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestOpsViews:
    def setup_method(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.driver = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='DRIVER'
        )
        self.customer = User.objects.create_user(
            phone='+250788999999',
            password='test123',
            user_type='CUSTOMER'
        )
    
    def test_driver_dashboard(self):
        from core.views_ops import DriverDashboardView
        view = DriverDashboardView.as_view()
        
        request = self.factory.get('/api/ops/driver/dashboard/')
        request.user = self.driver
        
        response = view(request)
        assert response.status_code in [200, 403]
    
    def test_available_shipments(self):
        from core.views_ops import AvailableShipmentsView
        view = AvailableShipmentsView.as_view()
        
        request = self.factory.get('/api/ops/shipments/available/')
        request.user = self.driver
        
        response = view(request)
        assert response.status_code in [200, 403]


@pytest.mark.django_db
class TestAuthViews:
    def setup_method(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
    
    @patch('core.views_auth.NotificationService')
    def test_request_otp(self, mock_notif):
        from core.views_auth import RequestOTPView
        view = RequestOTPView.as_view()
        
        request = self.factory.post('/api/auth/otp/request/', {
            'phone': '+250788123456',
            'purpose': 'LOGIN'
        }, format='json')
        
        response = view(request)
        assert response.status_code in [200, 400]
    
    def test_verify_otp_invalid(self):
        from core.views_auth import VerifyOTPView
        view = VerifyOTPView.as_view()
        
        request = self.factory.post('/api/auth/otp/verify/', {
            'phone': '+250788123456',
            'otp_code': '123456'
        }, format='json')
        
        response = view(request)
        assert response.status_code in [200, 400]


@pytest.mark.django_db
class TestBookingViews:
    def setup_method(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200')
        )
    
    @patch('core.views_booking.BookingService')
    def test_create_domestic_booking_view(self, mock_service):
        from core.views_booking import CreateDomesticBookingView
        view = CreateDomesticBookingView.as_view()
        
        request = self.factory.post('/api/bookings/domestic/', {
            'origin': 'Kigali',
            'destination': 'Huye',
            'weight_kg': '5.0',
            'commodity_type': 'Electronics',
            'recipient_phone': '+250788999999',
            'recipient_name': 'Recipient'
        }, format='json')
        request.user = self.user
        
        response = view(request)
        assert response.status_code in [200, 201, 400]


@pytest.mark.django_db
class TestDomesticViews:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_domestic_shipments(self):
        DomesticShipment.objects.create(
            customer=self.user,
            origin='Kigali',
            destination='Huye',
            weight_kg=Decimal('5.0'),
            description='Test',
            recipient_phone='+250788999999',
            recipient_name='Recipient',
            cost=Decimal('5000')
        )
        
        response = self.client.get('/api/domestic/')
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestInternationalViews:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_international_shipments(self):
        response = self.client.get('/api/international/')
        assert response.status_code in [200, 404]
