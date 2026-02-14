"""
Hybrid Authentication Backend for IshemaLink API.
Supports both Session Authentication (web dashboard) and JWT (mobile app).

Compliance: Implements dual-strategy authentication per NCSA guidelines.
"""
from typing import Optional, Tuple
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication, exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class HybridAuthentication(authentication.BaseAuthentication):
    """
    Hybrid authentication that tries Session first, then JWT.
    
    Priority:
    1. Session Authentication (for web dashboard agents/admins)
    2. JWT Bearer Token (for mobile drivers/customers)
    
    This allows flexible access while maintaining security standards.
    """
    
    def authenticate(self, request) -> Optional[Tuple[User, str]]:
        """
        Attempt authentication using multiple strategies.
        
        Args:
            request: Django HTTP request object
            
        Returns:
            Tuple of (user, auth_type) or None
        """
        # Strategy 1: Try Session Authentication first
        session_user = self._try_session_auth(request)
        if session_user:
            return (session_user, 'session')
        
        # Strategy 2: Try JWT Authentication
        jwt_user = self._try_jwt_auth(request)
        if jwt_user:
            return (jwt_user, 'jwt')
        
        # No authentication provided
        return None
    
    def _try_session_auth(self, request) -> Optional[User]:
        """
        Try session-based authentication.
        
        Args:
            request: HTTP request
            
        Returns:
            User object if authenticated, None otherwise
        """
        # Check if session has user ID
        if hasattr(request, 'session') and '_auth_user_id' in request.session:
            try:
                user_id = int(request.session['_auth_user_id'])
                return User.objects.get(id=user_id)
            except (User.DoesNotExist, ValueError, KeyError):
                pass
        return None
    
    def _try_jwt_auth(self, request) -> Optional[User]:
        """
        Try JWT bearer token authentication.
        
        Args:
            request: HTTP request
            
        Returns:
            User object if authenticated, None otherwise
        """
        jwt_authenticator = JWTAuthentication()
        
        try:
            # Extract and validate JWT token
            result = jwt_authenticator.authenticate(request)
            if result is not None:
                user, token = result
                # Store token info in request for audit logging
                request.jwt_token = token
                return user
        except (InvalidToken, TokenError, exceptions.AuthenticationFailed):
            # JWT validation failed, return None to allow other auth methods
            pass
        
        return None
    
    def authenticate_header(self, request) -> str:
        """
        Return authentication header for 401 responses.
        
        Args:
            request: HTTP request
            
        Returns:
            WWW-Authenticate header value
        """
        return 'Bearer realm="api"'


class PhoneBackend(ModelBackend):
    """
    Custom authentication backend using phone number instead of username.
    Supports Django admin login with phone numbers.
    """
    
    def authenticate(self, request, username: str = None, password: str = None, **kwargs) -> Optional[User]:
        """
        Authenticate user by phone number.
        
        Args:
            request: HTTP request
            username: Phone number (used as username)
            password: User password
            **kwargs: Additional arguments
            
        Returns:
            User object if authenticated, None otherwise
        """
        try:
            # Treat username as phone number
            user = User.objects.get(phone=username)
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        
        # Check password and active status
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User primary key
            
        Returns:
            User object or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
