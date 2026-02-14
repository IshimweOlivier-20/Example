"""
Core API views for authentication, identity verification, and privacy.

Compliance:
- Law N° 058/2021: Data Protection and Privacy Law
- NCSA Cybersecurity Guidelines
- RURA Telecommunications Regulations
"""
from typing import Dict, Any
import random
import json
from datetime import timedelta
from django.contrib.auth import get_user_model, authenticate
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q
from rest_framework import status, generics, views
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .serializers import (
    UserRegistrationSerializer, UserSerializer, 
    NIDVerificationSerializer, OTPRequestSerializer,
    OTPVerifySerializer, PasswordChangeSerializer,
    UserDataExportSerializer
)
from .validators import validate_rwanda_nid, validate_rwanda_phone, extract_birth_year_from_nid
from .models import OTPVerification, AuditLog
from .permissions import IsVerified

User = get_user_model()


# ============================================================================
# THROTTLE CLASSES
# ============================================================================

class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limit for login attempts.
    Prevents brute force attacks: 5 attempts per minute.
    
    Compliance: NCSA cybersecurity best practices
    """
    rate = '5/min'


class OTPRateThrottle(AnonRateThrottle):
    """Rate limit for OTP generation: 3 per hour per phone."""
    rate = '3/hour'


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

@extend_schema(
    summary="Session Login",
    description="Login for web dashboard users (Agents, Admins). Creates a session cookie.",
    request={"application/json": {"phone": "string", "password": "string"}},
    responses={
        200: OpenApiResponse(description="Login successful"),
        401: OpenApiResponse(description="Invalid credentials"),
    },
    tags=["Authentication"],
)
@api_view(['POST'])
@throttle_classes([LoginRateThrottle])
@permission_classes([AllowAny])
def login_session(request) -> Response:
    """
    POST /api/auth/login/session/
    Session-based login for web dashboard.
    
    Returns session cookie for browser-based authentication.
    """
    phone = request.data.get('phone')
    password = request.data.get('password')
    
    if not phone or not password:
        return Response({
            'error': 'Phone and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate user
    user = authenticate(request, username=phone, password=password)
    
    if user is None:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({
            'error': 'Account is disabled'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Create session using Django's built-in session framework
    from django.contrib.auth import login
    login(request, user)
    
    return Response({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'phone': user.phone,
            'user_type': user.user_type,
            'is_verified': user.is_verified,
        },
        'auth_method': 'session'
    })


@extend_schema(
    summary="Universal Logout",
    description="Logout for both session and JWT users. Blacklists JWT tokens if present.",
    responses={
        200: OpenApiResponse(description="Logout successful"),
    },
    tags=["Authentication"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request) -> Response:
    """
    POST /api/auth/logout/
    Universal logout - handles both session and JWT.
    
    For JWT: Blacklists the refresh token
    For Session: Destroys the session
    """
    # Handle JWT logout
    refresh_token = request.data.get('refresh_token')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass  # Token already invalid or blacklisted
    
    # Handle session logout
    if hasattr(request, 'session'):
        from django.contrib.auth import logout
        logout(request)
    
    return Response({
        'message': 'Logout successful'
    })


@extend_schema(
    summary="Get Current User",
    description="Returns current authenticated user details and authentication method.",
    responses={
        200: OpenApiResponse(description="User details"),
        401: OpenApiResponse(description="Not authenticated"),
    },
    tags=["Authentication"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whoami(request) -> Response:
    """
    GET /api/auth/whoami/
    Get current user details and auth method.
    """
    # Determine auth method
    auth_method = 'unknown'
    if hasattr(request, 'auth') and request.auth:
        auth_method = 'jwt'
    elif hasattr(request, 'session') and request.session.session_key:
        auth_method = 'session'
    
    serializer = UserSerializer(request.user)
    
    return Response({
        'user': serializer.data,
        'auth_method': auth_method,
        'timestamp': timezone.now().isoformat()
    })


@extend_schema(
    summary="Change Password",
    description="Change password for authenticated user.",
    request=PasswordChangeSerializer,
    responses={
        200: OpenApiResponse(description="Password changed successfully"),
        400: OpenApiResponse(description="Invalid data"),
    },
    tags=["Authentication"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request) -> Response:
    """
    POST /api/auth/password/change/
    Change user password (requires current password).
    """
    serializer = PasswordChangeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify current password
    if not request.user.check_password(serializer.validated_data['old_password']):
        return Response({
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    request.user.set_password(serializer.validated_data['new_password'])
    request.user.save()
    
    return Response({
        'message': 'Password changed successfully'
    })


# ============================================================================
# IDENTITY & KYC VIEWS
# ============================================================================

@extend_schema(
    summary="Register New User",
    description="Create new user account. OTP verification required before full access.",
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(description="User created, verify OTP to activate"),
        400: OpenApiResponse(description="Invalid data"),
    },
    tags=["Identity"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def register(request) -> Response:
    """
    POST /api/identity/register/
    Register new user account.
    
    Flow:
    1. Create user (is_verified=False)
    2. Generate OTP
    3. Return user ID and OTP reference
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    
    # Generate OTP for phone verification
    otp_code = _generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    
    OTPVerification.objects.create(
        phone=user.phone,
        otp_code=otp_code,
        purpose='REGISTRATION',
        expires_at=expires_at
    )
    
    # In production, send via SMS gateway
    # For development, return in response (REMOVE IN PRODUCTION)
    return Response({
        'message': 'User created. Verify your phone number with OTP.',
        'user_id': user.id,
        'phone': user.phone,
        'otp_code': otp_code,  # REMOVE IN PRODUCTION
        'expires_in_minutes': 5
    }, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Verify OTP Code",
    description="Verify OTP sent to phone number. Activates user account.",
    request=OTPVerifySerializer,
    responses={
        200: OpenApiResponse(description="OTP verified, user activated"),
        400: OpenApiResponse(description="Invalid or expired OTP"),
    },
    tags=["Identity"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request) -> Response:
    """
    POST /api/identity/verify-otp/
    Verify OTP code for phone number.
    """
    serializer = OTPVerifySerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    otp_code = serializer.validated_data['otp_code']
    
    # Find valid OTP
    otp = OTPVerification.objects.filter(
        phone=phone,
        otp_code=otp_code,
        is_used=False,
        expires_at__gt=timezone.now()
    ).first()
    
    if not otp:
        return Response({
            'error': 'Invalid or expired OTP code'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Mark OTP as used
    otp.is_used = True
    otp.used_at = timezone.now()
    otp.save()
    
    # Activate user if registration OTP
    if otp.purpose == 'REGISTRATION':
        try:
            user = User.objects.get(phone=phone)
            user.is_active = True
            user.save()
            
            return Response({
                'message': 'Phone verified. Account activated.',
                'user_id': user.id
            })
        except User.DoesNotExist:
            pass
    
    return Response({
        'message': 'OTP verified successfully'
    })


@extend_schema(
    summary="Submit NID for KYC",
    description="Submit Rwanda National ID for verification. Validates format and cross-checks birth year.",
    request=NIDVerificationSerializer,
    responses={
        200: OpenApiResponse(description="NID verified, user marked as verified"),
        400: OpenApiResponse(description="Invalid NID format"),
    },
    tags=["Identity"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kyc_nid(request) -> Response:
    """
    POST /api/identity/kyc/nid/
    Submit NID for KYC verification.
    
    Compliance: Law N° 058/2021 - KYC requirements
    Validates NID format and cross-checks birth year.
    """
    serializer = NIDVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    nid = serializer.validated_data['national_id']
    birth_year = serializer.validated_data.get('birth_year')
    
    # Validate NID with birth year cross-check
    is_valid, error = validate_rwanda_nid(nid, birth_year)
    
    if not is_valid:
        return Response({
            'error': error
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract birth year from NID if not provided
    if not birth_year:
        birth_year = extract_birth_year_from_nid(nid)
    
    # Update user
    user = request.user
    user.nid_number = nid
    user.birth_year = birth_year
    user.is_verified = True
    user.verification_date = timezone.now()
    user.save()
    
    return Response({
        'message': 'NID verified successfully',
        'is_verified': True,
        'verification_date': user.verification_date.isoformat()
    })


@extend_schema(
    summary="Get Verification Status",
    description="Check current user's verification status and missing requirements.",
    responses={
        200: OpenApiResponse(description="Verification status"),
    },
    tags=["Identity"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_status(request) -> Response:
    """
    GET /api/identity/status/
    Get current user's verification status.
    """
    user = request.user
    
    return Response({
        'is_verified': user.is_verified,
        'verification_date': user.verification_date.isoformat() if user.verification_date else None,
        'has_nid': bool(user.nid_number),
        'has_birth_year': bool(user.birth_year),
        'user_type': user.user_type,
        'assigned_sector': user.assigned_sector,
    })


@extend_schema(
    summary="Request OTP",
    description="Request new OTP for verification purposes (login, password reset, etc.).",
    request=OTPRequestSerializer,
    responses={
        200: OpenApiResponse(description="OTP sent"),
        429: OpenApiResponse(description="Rate limit exceeded"),
    },
    tags=["Identity"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def request_otp(request) -> Response:
    """
    POST /api/identity/otp/request/
    Generate and send OTP to phone number.
    """
    serializer = OTPRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    purpose = serializer.validated_data.get('purpose', 'LOGIN')
    
    # Generate OTP
    otp_code = _generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    
    OTPVerification.objects.create(
        phone=phone,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=expires_at
    )
    
    # Mock SMS send
    # In production: integrate with SMS gateway
    
    return Response({
        'message': f'OTP sent to {phone}',
        'otp_code': otp_code,  # REMOVE IN PRODUCTION
        'expires_in_minutes': 5
    })


# ============================================================================
# PRIVACY & DATA PROTECTION VIEWS
# ============================================================================

@extend_schema(
    summary="Export Personal Data",
    description="Download all personal data held by IshemaLink (GDPR-style data portability).",
    responses={
        200: OpenApiResponse(description="Personal data export"),
    },
    tags=["Privacy"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_my_data(request) -> Response:
    """
    GET /api/privacy/my-data/
    Export all user data (Right to Data Portability).
    
    Compliance: Law N° 058/2021 Article 28 - Right to data portability
    """
    user = request.user
    
    # Collect all user data
    data = {
        'user_profile': {
            'phone': user.phone,
            'full_name': user.full_name,
            'user_type': user.user_type,
            'is_verified': user.is_verified,
            'verification_date': user.verification_date.isoformat() if user.verification_date else None,
            'date_joined': user.date_joined.isoformat(),
            'assigned_sector': user.assigned_sector,
            'birth_year': user.birth_year,
        },
        'sensitive_data': {
            'nid_number': user.nid_number if user.nid_number else None,
            'tax_id': user.tax_id if user.tax_id else None,
        },
        'shipments': [],
        'audit_logs': [],
        'export_date': timezone.now().isoformat(),
        'export_format_version': '1.0'
    }
    
    # Add shipments
    from domestic.models import DomesticShipment
    shipments = DomesticShipment.objects.filter(customer=user)
    data['shipments'] = [
        {
            'tracking_number': s.tracking_number,
            'origin': s.origin,
            'destination': s.destination,
            'status': s.status,
            'created_at': s.created_at.isoformat(),
        }
        for s in shipments
    ]
    
    # Add audit logs (last 100)
    logs = AuditLog.objects.filter(user=user)[:100]
    data['audit_logs'] = [
        {
            'action': log.action,
            'resource': f"{log.resource_type}:{log.resource_id}",
            'timestamp': log.timestamp.isoformat(),
        }
        for log in logs
    ]
    
    return Response(data)


@extend_schema(
    summary="Anonymize Account",
    description="Request account deletion (Right to be Forgotten). Personal data will be redacted.",
    responses={
        200: OpenApiResponse(description="Account anonymized"),
    },
    tags=["Privacy"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def anonymize_account(request) -> Response:
    """
    POST /api/privacy/anonymize/
    Right to be Forgotten implementation.
    
    Compliance: Law N° 058/2021 Article 30 - Right to erasure
    """
    user = request.user
    
    # Anonymize user data
    user.anonymize()
    
    return Response({
        'message': 'Account has been anonymized',
        'note': 'Your personal data has been redacted. Shipment history is retained for legal compliance.'
    })


@extend_schema(
    summary="View Audit Logs",
    description="View audit logs of who accessed your data (Admin only: all logs).",
    responses={
        200: OpenApiResponse(description="Audit logs"),
    },
    tags=["Compliance"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs(request) -> Response:
    """
    GET /api/compliance/audit-logs/
    View audit trail (Glass Log).
    
    Regular users: see logs of their own data
    Admins/Gov: see all logs
    """
    user = request.user
    
    # Admin and Gov officials can see all logs
    if user.user_type in ['ADMIN', 'GOV_OFFICIAL']:
        logs = AuditLog.objects.all()[:100]
    else:
        # Regular users see logs related to their data
        logs = AuditLog.objects.filter(user=user)[:100]
    
    data = [
        {
            'id': log.id,
            'user_phone': log.user_phone,
            'user_type': log.user_type,
            'action': log.action,
            'resource': f"{log.resource_type}:{log.resource_id}",
            'endpoint': log.endpoint,
            'timestamp': log.timestamp.isoformat(),
            'ip_address': log.ip_address,
        }
        for log in logs
    ]
    
    return Response({
        'count': len(data),
        'logs': data
    })


@extend_schema(
    summary="View Consent History",
    description="View history of accepted terms and privacy policies.",
    responses={
        200: OpenApiResponse(description="Consent history"),
    },
    tags=["Privacy"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consent_history(request) -> Response:
    """
    GET /api/privacy/consent-history/
    View consent and terms acceptance history.
    """
    user = request.user
    
    return Response({
        'terms_accepted': user.terms_accepted,
        'terms_version': user.terms_version,
        'terms_accepted_at': user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
    })


# ============================================================================
# USER PROFILE & MANAGEMENT VIEWS
# ============================================================================

@extend_schema(
    summary="Get User Profile",
    description="Get current authenticated user's profile information.",
    responses={
        200: OpenApiResponse(description="User profile"),
    },
    tags=["Authentication"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request) -> Response:
    """
    GET /api/users/me/
    Get current user profile.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    summary="Agent Onboarding",
    description="Special registration endpoint for Agent users with sector assignment.",
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(description="Agent account created (pending approval)"),
        400: OpenApiResponse(description="Invalid data"),
    },
    tags=["Identity"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def agent_onboarding(request) -> Response:
    """
    POST /api/users/agents/onboard/
    Special endpoint for Agent onboarding with additional verification.
    
    Agents require:
    - NID number (mandatory)
    - Assigned sector (mandatory)
    - Admin approval before activation
    """
    # Force user_type to AGENT
    data = request.data.copy()
    data['user_type'] = 'AGENT'
    
    serializer = UserRegistrationSerializer(data=data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create agent but set is_active=False pending admin approval
    user = serializer.save()
    user.is_active = False
    user.save()
    
    return Response({
        'id': user.id,
        'phone': user.phone,
        'user_type': user.user_type,
        'assigned_sector': user.assigned_sector,
        'status': 'pending_approval',
        'message': 'Agent account created. Awaiting admin approval.'
    }, status=status.HTTP_201_CREATED)


# ============================================================================
# GOVERNMENT/RBAC VIEWS
# ============================================================================

@extend_schema(
    summary="Government Cargo Manifests",
    description="Read-only view of all shipments for government officials (RURA, RRA, NCSA).",
    responses={
        200: OpenApiResponse(description="Cargo manifests"),
        403: OpenApiResponse(description="Forbidden - Government access only"),
    },
    tags=["Government"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gov_manifests(request) -> Response:
    """
    GET /api/gov/manifests/
    Government view - read-only access to all cargo manifests.
    
    Restricted to GOV_OFFICIAL user type.
    """
    if request.user.user_type != 'GOV_OFFICIAL':
        return Response({
            'error': 'Access restricted to government officials'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Import models
    from domestic.models import DomesticShipment
    
    # Get all shipments
    shipments = DomesticShipment.objects.all()[:100]
    
    data = [
        {
            'tracking_number': s.tracking_number,
            'customer_phone': s.customer.phone,
            'origin': s.origin,
            'destination': s.destination,
            'weight_kg': float(s.weight_kg),
            'cost': float(s.cost),
            'status': s.status,
            'created_at': s.created_at.isoformat(),
        }
        for s in shipments
    ]
    
    return Response({
        'count': len(data),
        'manifests': data,
        'note': 'Read-only government view'
    })


@extend_schema(
    summary="Sector Statistics",
    description="Statistics for agent's assigned sector only.",
    responses={
        200: OpenApiResponse(description="Sector statistics"),
        403: OpenApiResponse(description="Forbidden - Agent access only"),
    },
    tags=["Operations"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sector_stats(request) -> Response:
    """
    GET /api/ops/sector-stats/
    Statistics for agent's assigned sector.
    
    Restricted to AGENT user type with assigned sector.
    """
    if request.user.user_type != 'AGENT':
        return Response({
            'error': 'Access restricted to sector agents'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.assigned_sector:
        return Response({
            'error': 'No sector assigned to this agent'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    sector = request.user.assigned_sector
    
    # Get shipments related to this sector
    from domestic.models import DomesticShipment
    
    shipments = DomesticShipment.objects.filter(
        Q(origin__icontains=sector) | Q(destination__icontains=sector)
    )
    
    stats = {
        'sector': sector,
        'total_shipments': shipments.count(),
        'pending': shipments.filter(status='PENDING').count(),
        'in_transit': shipments.filter(status='IN_TRANSIT').count(),
        'delivered': shipments.filter(status='DELIVERED').count(),
    }
    
    return Response(stats)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _generate_otp() -> str:
    """
    Generate 6-digit OTP code.
    
    Returns:
        6-digit string
    """
    return f"{random.randint(100000, 999999)}"
