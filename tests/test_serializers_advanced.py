import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from core.serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    NIDVerificationSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordChangeSerializer
)

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationSerializer:
    def test_valid_customer_registration(self):
        data = {
            'phone': '+250788123456',
            'password': 'Test@1234',
            'full_name': 'Test User',
            'user_type': 'CUSTOMER'
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()
        assert user.phone == '+250788123456'
        assert user.check_password('Test@1234')
    
    def test_invalid_phone_format(self):
        data = {
            'phone': '+254788123456',
            'password': 'Test@1234',
            'full_name': 'Test User',
            'user_type': 'CUSTOMER'
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone' in serializer.errors
    
    def test_agent_requires_nid(self):
        data = {
            'phone': '+250788123456',
            'password': 'Test@1234',
            'full_name': 'Test Agent',
            'user_type': 'AGENT'
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'nid_number' in serializer.errors
    
    def test_agent_requires_sector(self):
        data = {
            'phone': '+250788123456',
            'password': 'Test@1234',
            'full_name': 'Test Agent',
            'user_type': 'AGENT',
            'nid_number': '1199870123456789'
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'assigned_sector' in serializer.errors
    
    def test_valid_agent_registration(self):
        data = {
            'phone': '+250788123456',
            'password': 'Test@1234',
            'full_name': 'Test Agent',
            'user_type': 'AGENT',
            'nid_number': '1199870123456789',
            'assigned_sector': 'Gasabo'
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
    
    def test_birth_year_mismatch(self):
        data = {
            'phone': '+250788123456',
            'password': 'Test@1234',
            'full_name': 'Test User',
            'user_type': 'CUSTOMER',
            'nid_number': '1199870123456789',
            'birth_year': 1990
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'birth_year' in serializer.errors


@pytest.mark.django_db
class TestUserSerializer:
    def test_user_serializer_read(self):
        user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            full_name='Test User',
            user_type='CUSTOMER'
        )
        serializer = UserSerializer(user)
        data = serializer.data
        assert data['phone'] == '+250788123456'
        assert data['full_name'] == 'Test User'
        assert 'password' not in data


class TestNIDVerificationSerializer:
    def test_valid_nid(self):
        data = {
            'national_id': '1199870123456789',
            'birth_year': 1998
        }
        serializer = NIDVerificationSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_nid_format(self):
        data = {
            'national_id': '119987012345',
            'birth_year': 1998
        }
        serializer = NIDVerificationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'national_id' in serializer.errors


class TestOTPRequestSerializer:
    def test_valid_otp_request(self):
        data = {
            'phone': '+250788123456',
            'purpose': 'LOGIN'
        }
        serializer = OTPRequestSerializer(data=data)
        assert serializer.is_valid()
    
    def test_invalid_phone(self):
        data = {
            'phone': '+254788123456',
            'purpose': 'LOGIN'
        }
        serializer = OTPRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone' in serializer.errors


class TestOTPVerifySerializer:
    def test_valid_otp_verify(self):
        data = {
            'phone': '+250788123456',
            'otp_code': '123456'
        }
        serializer = OTPVerifySerializer(data=data)
        assert serializer.is_valid()
    
    def test_invalid_otp_length(self):
        data = {
            'phone': '+250788123456',
            'otp_code': '123'
        }
        serializer = OTPVerifySerializer(data=data)
        assert not serializer.is_valid()
    
    def test_non_numeric_otp(self):
        data = {
            'phone': '+250788123456',
            'otp_code': 'ABC123'
        }
        serializer = OTPVerifySerializer(data=data)
        assert not serializer.is_valid()
        assert 'otp_code' in serializer.errors


class TestPasswordChangeSerializer:
    def test_valid_password_change(self):
        data = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'NewPass@123'
        }
        serializer = PasswordChangeSerializer(data=data)
        assert serializer.is_valid()
    
    def test_password_mismatch(self):
        data = {
            'old_password': 'OldPass@123',
            'new_password': 'NewPass@123',
            'confirm_password': 'DifferentPass@123'
        }
        serializer = PasswordChangeSerializer(data=data)
        assert not serializer.is_valid()
        assert 'confirm_password' in serializer.errors
