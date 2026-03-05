import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAuthBackends:
    def setup_method(self):
        from ishemalink.auth_backends import PhoneBackend
        self.backend = PhoneBackend()
        self.user = User.objects.create_user(
            phone='+250788123456',
            password='test123',
            user_type='CUSTOMER'
        )
    
    def test_authenticate_valid_credentials(self):
        user = self.backend.authenticate(
            request=None,
            username='+250788123456',
            password='test123'
        )
        assert user is not None
        assert user.phone == '+250788123456'
    
    def test_authenticate_invalid_password(self):
        user = self.backend.authenticate(
            request=None,
            username='+250788123456',
            password='wrongpassword'
        )
        assert user is None
    
    def test_authenticate_invalid_phone(self):
        user = self.backend.authenticate(
            request=None,
            username='+250788999999',
            password='test123'
        )
        assert user is None
    
    def test_authenticate_missing_phone(self):
        user = self.backend.authenticate(
            request=None,
            username=None,
            password='test123'
        )
        assert user is None
    
    def test_authenticate_missing_password(self):
        user = self.backend.authenticate(
            request=None,
            username='+250788123456',
            password=None
        )
        assert user is None
    
    def test_get_user_valid(self):
        user = self.backend.get_user(self.user.id)
        assert user is not None
        assert user.id == self.user.id
    
    def test_get_user_invalid(self):
        user = self.backend.get_user(99999)
        assert user is None
