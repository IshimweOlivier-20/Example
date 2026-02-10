"""
URL configuration for ishemalink project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.db import connection
from django.utils import timezone


@api_view(['GET'])
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
    
    # App routes
    path('api/auth/', include('core.urls')),
    path('api/domestic/', include('domestic.urls')),
    path('api/international/', include('international.urls')),
    path('api/shipments/', include('domestic.urls')),  # Shared shipment routes
    
    # Pricing routes
    path('api/pricing/', include('core.pricing_urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
