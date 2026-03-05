import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from rest_framework.test import APIRequestFactory
from core.middleware import (
    get_client_ip,
    is_sensitive_endpoint,
    extract_resource_info,
    AuditLoggingMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMetadataMiddleware
)
from core.permissions import IsCustomer, IsDriver, IsAdmin, IsAgent

User = get_user_model()


class TestMiddlewareHelpers:
    def test_get_client_ip_direct(self):
        request = HttpRequest()
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        assert get_client_ip(request) == '192.168.1.1'
    
    def test_get_client_ip_forwarded(self):
        request = HttpRequest()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '10.0.0.1, 192.168.1.1',
            'REMOTE_ADDR': '192.168.1.1'
        }
        assert get_client_ip(request) == '10.0.0.1'
    
    def test_is_sensitive_endpoint_shipments(self):
        assert is_sensitive_endpoint('/api/domestic/shipments/123/') is True
        assert is_sensitive_endpoint('/api/international/shipments/456/') is True
        assert is_sensitive_endpoint('/api/shipments/789/') is True
    
    def test_is_sensitive_endpoint_users(self):
        assert is_sensitive_endpoint('/api/users/123/') is True
        assert is_sensitive_endpoint('/api/users/me/') is True
    
    def test_is_sensitive_endpoint_billing(self):
        assert is_sensitive_endpoint('/api/billing/') is True
    
    def test_is_sensitive_endpoint_privacy(self):
        assert is_sensitive_endpoint('/api/privacy/my-data/') is True
    
    def test_is_sensitive_endpoint_identity(self):
        assert is_sensitive_endpoint('/api/identity/status/') is True
    
    def test_is_sensitive_endpoint_public(self):
        assert is_sensitive_endpoint('/api/public/') is False
        assert is_sensitive_endpoint('/api/health/') is False
    
    def test_extract_resource_info_shipments(self):
        resource_type, resource_id = extract_resource_info('/api/shipments/123/')
        assert resource_type == 'shipments'
        assert resource_id == '123'
    
    def test_extract_resource_info_users(self):
        resource_type, resource_id = extract_resource_info('/api/users/456/')
        assert resource_type == 'users'
        assert resource_id == '456'
    
    def test_extract_resource_info_me(self):
        resource_type, resource_id = extract_resource_info('/api/users/me/')
        assert resource_type == 'user_profile'
        assert resource_id == 'me'
    
    def test_extract_resource_info_unknown(self):
        resource_type, resource_id = extract_resource_info('/api/unknown/')
        assert resource_type == 'unknown'
        assert resource_id == ''


@pytest.mark.django_db
class TestAuditLoggingMiddleware:
    def test_audit_middleware_non_sensitive(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = AuditLoggingMiddleware(get_response)
        
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/public/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = Mock(is_authenticated=False)
        
        response = middleware(request)
        assert response is not None
    
    def test_audit_middleware_sensitive_unauthenticated(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = AuditLoggingMiddleware(get_response)
        
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/shipments/123/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = Mock(is_authenticated=False)
        
        response = middleware(request)
        assert response is not None
    
    def test_audit_middleware_sensitive_authenticated(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
        
        get_response = Mock(return_value=HttpResponse(status=200))
        middleware = AuditLoggingMiddleware(get_response)
        
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/shipments/123/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 200


class TestSecurityHeadersMiddleware:
    def test_security_headers_added(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = SecurityHeadersMiddleware(get_response)
        
        request = HttpRequest()
        response = middleware(request)
        
        assert 'Strict-Transport-Security' in response
        assert 'X-Content-Type-Options' in response
        assert 'X-Frame-Options' in response
        assert 'X-XSS-Protection' in response
        assert 'Content-Security-Policy' in response
        assert 'Referrer-Policy' in response


class TestRateLimitMetadataMiddleware:
    def test_rate_limit_no_metadata(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = RateLimitMetadataMiddleware(get_response)
        
        request = HttpRequest()
        response = middleware(request)
        assert response is not None
    
    def test_rate_limit_with_metadata(self):
        get_response = Mock(return_value=HttpResponse())
        middleware = RateLimitMetadataMiddleware(get_response)
        
        request = HttpRequest()
        request.throttle_metadata = {
            'limit': 100,
            'remaining': 95,
            'reset': 1234567890
        }
        
        response = middleware(request)
        assert 'X-RateLimit-Limit' in response
        assert 'X-RateLimit-Remaining' in response
        assert 'X-RateLimit-Reset' in response


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
        self.agent = User.objects.create_user(
            phone='+250788333333',
            password='test123',
            user_type='AGENT'
        )
        self.admin = User.objects.create_user(
            phone='+250788444444',
            password='test123',
            user_type='ADMIN',
            is_staff=True
        )
    
    def test_is_customer_allowed(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_customer_denied(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_driver_allowed(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_driver_denied(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_agent_allowed(self):
        permission = IsAgent()
        request = self.factory.get('/api/test/')
        request.user = self.agent
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_agent_denied(self):
        permission = IsAgent()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_admin_allowed(self):
        permission = IsAdmin()
        request = self.factory.get('/api/test/')
        request.user = self.admin
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_admin_denied(self):
        permission = IsAdmin()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
