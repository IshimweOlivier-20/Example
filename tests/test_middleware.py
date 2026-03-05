import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from rest_framework.test import APIRequestFactory
from core.middleware import AuditLoggingMiddleware, SecurityHeadersMiddleware
from core.permissions import IsCustomer, IsDriver, IsAdmin

User = get_user_model()


@pytest.mark.django_db
class TestMiddleware:
    def test_audit_logging_middleware(self):
        get_response = Mock(return_value=Mock(status_code=200))
        middleware = AuditLoggingMiddleware(get_response)
        
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/test/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = Mock(is_authenticated=False)
        
        response = middleware(request)
        assert response.status_code == 200

    def test_security_headers_middleware(self):
        from django.http import HttpResponse
        get_response = Mock(return_value=HttpResponse())
        middleware = SecurityHeadersMiddleware(get_response)
        
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/test/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        response = middleware(request)
        assert 'Strict-Transport-Security' in response


@pytest.mark.django_db
class TestPermissions:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            phone='+250788111111',
            password='test123',
            user_type='CUSTOMER'
        )
        self.driver = User.objects.create_user(
            phone='+250788222222',
            password='test123',
            user_type='DRIVER'
        )
        self.admin = User.objects.create_user(
            phone='+250788333333',
            password='test123',
            user_type='ADMIN',
            is_staff=True
        )

    def test_is_customer_permission(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        
        view = Mock()
        assert permission.has_permission(request, view) is True

    def test_is_customer_permission_denied(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        
        view = Mock()
        assert permission.has_permission(request, view) is False

    def test_is_driver_permission(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        
        view = Mock()
        assert permission.has_permission(request, view) is True

    def test_is_admin_permission(self):
        permission = IsAdmin()
        request = self.factory.get('/api/test/')
        request.user = self.admin
        
        view = Mock()
        assert permission.has_permission(request, view) is True
