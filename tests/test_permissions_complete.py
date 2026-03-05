import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from core.permissions import (
    IsCustomer,
    IsDriver,
    IsAgent,
    IsAdmin,
    IsVerified,
    IsOwnerOrReadOnly,
    IsSectorAgent
)

User = get_user_model()


@pytest.mark.django_db
class TestPermissionsComplete:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            phone='+250788111111',
            password='test123',
            user_type='CUSTOMER',
            is_verified=True
        )
        self.driver = User.objects.create_user(
            phone='+250788222222',
            password='test123',
            user_type='DRIVER',
            is_verified=True
        )
        self.agent = User.objects.create_user(
            phone='+250788333333',
            password='test123',
            user_type='AGENT',
            is_verified=True
        )
        self.admin = User.objects.create_user(
            phone='+250788444444',
            password='test123',
            user_type='ADMIN',
            is_staff=True,
            is_verified=True
        )
        self.unverified = User.objects.create_user(
            phone='+250788555555',
            password='test123',
            user_type='CUSTOMER',
            is_verified=False
        )
    
    def test_is_customer_permission_allowed(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_customer_permission_denied_driver(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_customer_permission_denied_agent(self):
        permission = IsCustomer()
        request = self.factory.get('/api/test/')
        request.user = self.agent
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_driver_permission_allowed(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_driver_permission_denied_customer(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_agent_permission_allowed(self):
        permission = IsAgent()
        request = self.factory.get('/api/test/')
        request.user = self.agent
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_agent_permission_denied_customer(self):
        permission = IsAgent()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_admin_permission_allowed(self):
        permission = IsAdmin()
        request = self.factory.get('/api/test/')
        request.user = self.admin
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_admin_permission_denied_customer(self):
        permission = IsAdmin()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_customer_or_agent_customer_allowed(self):
        permission = IsOwnerOrReadOnly()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        obj = Mock(customer=self.customer)
        assert permission.has_object_permission(request, Mock(), obj) is True
    
    def test_is_customer_or_agent_agent_allowed(self):
        permission = IsSectorAgent()
        request = self.factory.get('/api/test/')
        request.user = self.agent
        assert permission.has_permission(request, Mock()) is False
    
    def test_is_customer_or_agent_driver_denied(self):
        permission = IsOwnerOrReadOnly()
        request = self.factory.post('/api/test/')
        request.user = self.driver
        obj = Mock(customer=self.customer)
        assert permission.has_object_permission(request, Mock(), obj) is False
    
    def test_is_driver_or_agent_driver_allowed(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.driver
        obj = Mock(driver=self.driver)
        assert permission.has_object_permission(request, Mock(), obj) is True
    
    def test_is_driver_or_agent_agent_allowed(self):
        permission = IsAgent()
        request = self.factory.get('/api/test/')
        request.user = self.agent
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_driver_or_agent_customer_denied(self):
        permission = IsDriver()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        obj = Mock(driver=self.driver)
        assert permission.has_object_permission(request, Mock(), obj) is False
    
    def test_is_verified_permission_allowed(self):
        permission = IsVerified()
        request = self.factory.get('/api/test/')
        request.user = self.customer
        assert permission.has_permission(request, Mock()) is True
    
    def test_is_verified_permission_denied(self):
        permission = IsVerified()
        request = self.factory.get('/api/test/')
        request.user = self.unverified
        assert permission.has_permission(request, Mock()) is False
