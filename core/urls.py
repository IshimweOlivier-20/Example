"""
URL configuration for core app (authentication and user management).
Implements comprehensive security endpoints per Formative 2 requirements.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views_auth as views

urlpatterns = [
    # ========================================================================
    # AUTHENTICATION ENDPOINTS
    # ========================================================================
    # Session-based auth (web dashboard)
    path('login/session/', views.login_session, name='login-session'),
    
    # JWT auth (mobile app)
    path('token/obtain/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Universal logout
    path('logout/', views.logout_view, name='logout'),
    
    # User info
    path('whoami/', views.whoami, name='whoami'),
    
    # Password management
    path('password/change/', views.change_password, name='password-change'),
    
    # ========================================================================
    # IDENTITY & KYC ENDPOINTS
    # ========================================================================
    path('identity/register/', views.register, name='identity-register'),
    path('identity/verify-otp/', views.verify_otp, name='identity-verify-otp'),
    path('identity/kyc/nid/', views.kyc_nid, name='identity-kyc-nid'),
    path('identity/status/', views.verification_status, name='identity-status'),
    path('identity/otp/request/', views.request_otp, name='identity-otp-request'),
    
    # ========================================================================
    # PRIVACY & DATA PROTECTION ENDPOINTS
    # ========================================================================
    path('privacy/my-data/', views.export_my_data, name='privacy-export'),
    path('privacy/anonymize/', views.anonymize_account, name='privacy-anonymize'),
    path('privacy/consent-history/', views.consent_history, name='privacy-consent'),
    
    # ========================================================================
    # COMPLIANCE & AUDIT ENDPOINTS
    # ========================================================================
    path('compliance/audit-logs/', views.audit_logs, name='compliance-audit-logs'),
    
    # ========================================================================
    # GOVERNMENT & RBAC ENDPOINTS
    # ========================================================================
    path('gov/manifests/', views.gov_manifests, name='gov-manifests'),
    path('ops/sector-stats/', views.sector_stats, name='ops-sector-stats'),
]
