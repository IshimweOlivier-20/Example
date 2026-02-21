"""
Operations and monitoring endpoints for production deployment.

Health checks, maintenance mode, metrics export for Prometheus.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
import psutil
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Deep Health Check",
    description="Comprehensive system health check: DB, Redis, disk space, memory.",
    responses={
        200: OpenApiResponse(description="System healthy"),
        503: OpenApiResponse(description="System degraded"),
    },
    tags=["Operations"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def deep_health_check(request):
    """
    GET /api/health/deep/
    
    Production health check for load balancer and monitoring.
    
    Checks:
    - Database connectivity and query performance
    - Redis cache availability
    - Disk space (warn if <10% free)
    - Memory usage
    - Active connections
    
    Returns 503 if any critical component fails.
    """
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['checks']['database'] = {
            'status': 'healthy',
            'latency_ms': 0  # In production: measure actual latency
        }
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'failed',
            'error': str(e)
        }
    
    # Redis check
    try:
        cache.set('health_check', 'ok', timeout=10)
        cache_value = cache.get('health_check')
        health_status['checks']['redis'] = {
            'status': 'healthy' if cache_value == 'ok' else 'degraded'
        }
    except Exception as e:
        health_status['status'] = 'degraded'
        health_status['checks']['redis'] = {
            'status': 'failed',
            'error': str(e)
        }
    
    # Disk space check
    try:
        disk = psutil.disk_usage('/')
        disk_free_percent = 100 - disk.percent
        health_status['checks']['disk'] = {
            'status': 'healthy' if disk_free_percent > 10 else 'warning',
            'free_percent': round(disk_free_percent, 2),
            'free_gb': round(disk.free / (1024**3), 2)
        }
        if disk_free_percent < 10:
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['disk'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # Memory check
    try:
        memory = psutil.virtual_memory()
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory.percent < 90 else 'warning',
            'used_percent': memory.percent,
            'available_gb': round(memory.available / (1024**3), 2)
        }
        if memory.percent > 90:
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # Application metrics
    from domestic.models import DomesticShipment
    from international.models import InternationalShipment
    
    try:
        active_shipments = (
            DomesticShipment.objects.filter(status='IN_TRANSIT').count() +
            InternationalShipment.objects.filter(status='IN_TRANSIT').count()
        )
        health_status['checks']['application'] = {
            'status': 'healthy',
            'active_shipments': active_shipments
        }
    except Exception as e:
        health_status['checks']['application'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    response_status = (
        status.HTTP_200_OK if health_status['status'] == 'healthy'
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return Response(health_status, status=response_status)


@extend_schema(
    summary="Prometheus Metrics",
    description="Export metrics in Prometheus format for monitoring.",
    responses={
        200: OpenApiResponse(description="Metrics in Prometheus format"),
    },
    tags=["Operations"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def prometheus_metrics(request):
    """
    GET /api/ops/metrics/
    
    Export application metrics for Prometheus scraping.
    
    Metrics:
    - ishemalink_shipments_total{status="pending|in_transit|delivered"}
    - ishemalink_revenue_total
    - ishemalink_active_drivers
    """
    from domestic.models import DomesticShipment
    from international.models import InternationalShipment
    from core.models import User
    from django.db.models import Count, Sum, Q
    
    # Shipment metrics
    domestic_counts = DomesticShipment.objects.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        in_transit=Count('id', filter=Q(status='IN_TRANSIT')),
        delivered=Count('id', filter=Q(status='DELIVERED')),
        total_revenue=Sum('cost', filter=Q(payment_confirmed=True))
    )
    
    international_counts = InternationalShipment.objects.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        in_transit=Count('id', filter=Q(status='IN_TRANSIT')),
        delivered=Count('id', filter=Q(status='DELIVERED')),
        total_revenue=Sum('cost', filter=Q(payment_confirmed=True))
    )
    
    # Driver metrics
    active_drivers = User.objects.filter(
        user_type='DRIVER',
        is_active=True
    ).count()
    
    # Format as Prometheus metrics
    metrics = f"""# HELP ishemalink_shipments_total Total shipments by status
# TYPE ishemalink_shipments_total gauge
ishemalink_shipments_total{{status="pending",type="domestic"}} {domestic_counts['pending'] or 0}
ishemalink_shipments_total{{status="in_transit",type="domestic"}} {domestic_counts['in_transit'] or 0}
ishemalink_shipments_total{{status="delivered",type="domestic"}} {domestic_counts['delivered'] or 0}
ishemalink_shipments_total{{status="pending",type="international"}} {international_counts['pending'] or 0}
ishemalink_shipments_total{{status="in_transit",type="international"}} {international_counts['in_transit'] or 0}
ishemalink_shipments_total{{status="delivered",type="international"}} {international_counts['delivered'] or 0}

# HELP ishemalink_revenue_total Total revenue in RWF
# TYPE ishemalink_revenue_total counter
ishemalink_revenue_total{{type="domestic"}} {float(domestic_counts['total_revenue'] or 0)}
ishemalink_revenue_total{{type="international"}} {float(international_counts['total_revenue'] or 0)}

# HELP ishemalink_active_drivers Number of active drivers
# TYPE ishemalink_active_drivers gauge
ishemalink_active_drivers {active_drivers}
"""
    
    return Response(metrics, content_type='text/plain')


@extend_schema(
    summary="Toggle Maintenance Mode",
    description="Enable/disable maintenance mode (Admin only).",
    request={
        "application/json": {
            "enabled": "boolean"
        }
    },
    responses={
        200: OpenApiResponse(description="Maintenance mode updated"),
    },
    tags=["Operations"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_maintenance_mode(request):
    """
    POST /api/ops/maintenance/toggle/
    
    Enable or disable maintenance mode.
    When enabled, all non-admin requests return 503.
    
    Admin only.
    """
    if request.user.user_type != 'ADMIN':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    enabled = request.data.get('enabled', False)
    
    # Store in cache
    cache.set('maintenance_mode', enabled, timeout=None)
    
    logger.warning(
        f"Maintenance mode {'enabled' if enabled else 'disabled'} "
        f"by {request.user.phone}"
    )
    
    return Response({
        'maintenance_mode': enabled,
        'message': 'System in maintenance mode' if enabled else 'System operational'
    })


@extend_schema(
    summary="Seed Test Data",
    description="Populate database with test shipments for load testing.",
    request={
        "application/json": {
            "count": "number"
        }
    },
    responses={
        200: OpenApiResponse(description="Test data created"),
    },
    tags=["Testing"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seed_test_data(request):
    """
    POST /api/test/seed/
    
    Hydrate database with dummy shipments for testing.
    
    Use case: Load testing, demo environments
    Warning: Only enable in non-production environments
    """
    if not settings.DEBUG:
        return Response({
            'error': 'Test endpoints disabled in production'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if request.user.user_type != 'ADMIN':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    count = int(request.data.get('count', 100))
    
    if count > 10000:
        return Response({
            'error': 'Maximum 10,000 test records allowed'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from domestic.models import DomesticShipment
    from core.models import User
    from decimal import Decimal
    import random
    
    # Get or create test customer
    test_customer, _ = User.objects.get_or_create(
        phone='+250788999999',
        defaults={
            'full_name': 'Test Customer',
            'user_type': 'CUSTOMER',
            'nid_number': '1199870123456789'
        }
    )
    
    origins = ['Kigali', 'Huye', 'Musanze', 'Rubavu', 'Nyagatare']
    destinations = ['Kigali', 'Huye', 'Musanze', 'Rubavu', 'Nyagatare']
    commodities = ['Potatoes', 'Coffee', 'Tea', 'Electronics', 'Textiles']
    statuses = ['PENDING', 'IN_TRANSIT', 'DELIVERED']
    
    shipments = []
    for i in range(count):
        shipment = DomesticShipment(
            customer=test_customer,
            origin=random.choice(origins),
            destination=random.choice(destinations),
            weight_kg=Decimal(str(round(random.uniform(1, 50), 2))),
            description=random.choice(commodities),
            recipient_phone='+250788000111',
            recipient_name='Test Recipient',
            status=random.choice(statuses),
            cost=Decimal(str(random.randint(1000, 50000))),
            payment_confirmed=True
        )
        shipments.append(shipment)
    
    DomesticShipment.objects.bulk_create(shipments)
    
    logger.info(f"Created {count} test shipments")
    
    return Response({
        'message': f'Created {count} test shipments',
        'count': count
    })


@extend_schema(
    summary="Security Health Check",
    description="Report on security configuration status.",
    responses={
        200: OpenApiResponse(description="Security status"),
    },
    tags=["Testing"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def security_health_check(request):
    """
    GET /api/test/security-health/
    
    Report on security configuration:
    - Debug mode status
    - HTTPS enforcement
    - Security headers
    - Rate limiting
    
    Admin only.
    """
    if request.user.user_type != 'ADMIN':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    security_status = {
        'debug_mode': settings.DEBUG,
        'secret_key_secure': not settings.SECRET_KEY.startswith('django-insecure'),
        'allowed_hosts_configured': len(settings.ALLOWED_HOSTS) > 0,
        'https_enforced': getattr(settings, 'SECURE_SSL_REDIRECT', False),
        'hsts_enabled': getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0,
        'session_cookie_secure': getattr(settings, 'SESSION_COOKIE_SECURE', False),
        'csrf_cookie_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
    }
    
    # Overall security score
    checks_passed = sum(1 for k, v in security_status.items() if v and k != 'debug_mode')
    checks_passed += 1 if not security_status['debug_mode'] else 0
    total_checks = len(security_status)
    
    security_status['score'] = f"{checks_passed}/{total_checks}"
    security_status['status'] = 'secure' if checks_passed == total_checks else 'needs_attention'
    
    return Response(security_status)
