"""
URL configuration for ishemalink project.
Integrated and consolidated for Formative 2.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.db import connection
from django.utils import timezone
from core import views_auth as views  # Use consolidated views_auth
from core import pricing_views
from core import views_booking, views_admin, views_ops


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    API root endpoint with version information.
    """
    return Response({
        'version': 'v1',
        'name': 'IshemaLink API',
        'description': 'Logistics platform API for Rwanda',
        'endpoints': {
            'health': '/api/status/',
            'auth': '/api/auth/',
            'domestic': '/api/domestic/',
            'international': '/api/international/',
            'pricing': '/api/pricing/',
            'shipments': '/api/shipments/',
            'documentation': '/api/docs/',
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    System health check and database connectivity check.
    """
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected',
            'version': 'v1',
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'failed',
            'error': str(e),
        }, status=503)


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', api_root, name='api-root'),
    path('api/status/', health_check, name='health-check'),
    
    # Auth routes
    path('api/auth/', include('core.urls')),
    
    # User routes
    path('api/users/me/', views.user_profile, name='user-profile'),
    path('api/users/agents/onboard/', views.agent_onboarding, name='agent-onboard'),
    
    # Shipment routes
    path('api/domestic/', include('domestic.urls')),
    path('api/international/', include('international.urls')),
    path('api/shipments/', include('shipments.urls')),
    
    # Billing routes
    path('api/billing/', include('billing.urls')),
    
    # Pricing routes
    path('api/pricing/', include('core.pricing_urls')),
    path('api/admin/cache/clear-tariffs/', pricing_views.clear_cache, name='clear-cache'),
    
    # Grand Integration: Booking & Payment
    path('api/shipments/create/', views_booking.create_shipment, name='create-shipment'),
    path('api/payments/initiate/', views_booking.initiate_payment, name='initiate-payment'),
    path('api/payments/webhook/', views_booking.payment_webhook, name='payment-webhook'),
    path('api/tracking/<str:tracking_code>/live/', views_booking.track_shipment_live, name='track-live'),
    path('api/notifications/broadcast/', views_booking.broadcast_notification, name='broadcast-notification'),
    
    # Admin Dashboard
    path('api/admin/dashboard/summary/', views_admin.admin_dashboard_summary, name='admin-dashboard'),
    
    # Analytics Endpoints
    path('api/analytics/routes/top/', views_admin.analytics_top_routes, name='analytics-routes'),
    path('api/analytics/commodities/breakdown/', views_admin.analytics_commodity_breakdown, name='analytics-commodities'),
    path('api/analytics/revenue/heatmap/', views_admin.analytics_revenue_heatmap, name='analytics-revenue'),
    path('api/analytics/drivers/leaderboard/', views_admin.analytics_driver_leaderboard, name='analytics-drivers'),
    
    # Government Integration
    path('api/gov/ebm/verify-receipt/<str:ebm_receipt_number>/', views_admin.gov_ebm_verify_receipt, name='gov-ebm-verify'),
    path('api/gov/rura/verify-license/<str:license_no>/', views_admin.gov_rura_verify_license, name='gov-rura-license'),
    path('api/gov/customs/generate-manifest/', views_admin.gov_generate_customs_manifest, name='gov-customs-manifest'),
    path('api/gov/audit/access-log/', views_admin.gov_audit_access_log, name='gov-audit-log'),
    
    # Operations & Monitoring
    path('api/health/deep/', views_ops.deep_health_check, name='deep-health'),
    path('api/ops/metrics/', views_ops.prometheus_metrics, name='prometheus-metrics'),
    path('api/ops/maintenance/toggle/', views_ops.toggle_maintenance_mode, name='maintenance-toggle'),
    
    # Testing Endpoints
    path('api/test/seed/', views_ops.seed_test_data, name='test-seed'),
    path('api/test/security-health/', views_ops.security_health_check, name='security-health'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
