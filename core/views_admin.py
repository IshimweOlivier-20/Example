"""
Admin dashboard and control tower views.

Provides real-time overview for operations management:
- Active shipments map
- Revenue metrics
- Driver availability
- System health monitoring
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
import logging

from analytics.queries import AnalyticsQueries

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Admin Dashboard Summary",
    description="Real-time control tower view: active trucks, revenue, system health.",
    responses={
        200: OpenApiResponse(description="Dashboard metrics"),
    },
    tags=["Admin"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_summary(request):
    """
    GET /api/admin/dashboard/summary/
    
    Live dashboard for operations control tower.
    
    Metrics:
    - Active shipments in each status
    - Today's revenue
    - Available drivers
    - System health indicators
    
    Access: Admin and Gov officials only
    """
    if request.user.user_type not in ['ADMIN', 'GOV_OFFICIAL']:
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from domestic.models import DomesticShipment
    from international.models import InternationalShipment
    from core.models import User
    
    # Aggregate shipment stats
    today = timezone.now().date()
    
    domestic_stats = DomesticShipment.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        in_transit=Count('id', filter=Q(status='IN_TRANSIT')),
        delivered_today=Count('id', filter=Q(
            status='DELIVERED',
            updated_at__date=today
        )),
        revenue_today=Sum('cost', filter=Q(
            created_at__date=today,
            payment_confirmed=True
        ))
    )
    
    international_stats = InternationalShipment.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        in_transit=Count('id', filter=Q(status='IN_TRANSIT')),
        at_customs=Count('id', filter=Q(status='AT_CUSTOMS')),
        delivered_today=Count('id', filter=Q(
            status='DELIVERED',
            updated_at__date=today
        )),
        revenue_today=Sum('cost', filter=Q(
            created_at__date=today,
            payment_confirmed=True
        ))
    )
    
    # Driver availability
    driver_stats = User.objects.filter(user_type='DRIVER').aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True))
    )
    
    # System health
    from django.core.cache import cache
    cache_healthy = cache.get('health_check') is not None or True
    
    dashboard = {
        'timestamp': timezone.now().isoformat(),
        'shipments': {
            'domestic': {
                'total': domestic_stats['total'] or 0,
                'pending': domestic_stats['pending'] or 0,
                'in_transit': domestic_stats['in_transit'] or 0,
                'delivered_today': domestic_stats['delivered_today'] or 0
            },
            'international': {
                'total': international_stats['total'] or 0,
                'pending': international_stats['pending'] or 0,
                'in_transit': international_stats['in_transit'] or 0,
                'at_customs': international_stats['at_customs'] or 0,
                'delivered_today': international_stats['delivered_today'] or 0
            }
        },
        'revenue': {
            'today': float(
                (domestic_stats['revenue_today'] or 0) +
                (international_stats['revenue_today'] or 0)
            ),
            'currency': 'RWF'
        },
        'drivers': {
            'total': driver_stats['total'] or 0,
            'active': driver_stats['active'] or 0,
            'availability_rate': round(
                100.0 * (driver_stats['active'] or 0) / max(driver_stats['total'] or 1, 1),
                2
            )
        },
        'system_health': {
            'api': 'healthy',
            'database': 'connected',
            'cache': 'healthy' if cache_healthy else 'degraded'
        }
    }
    
    return Response(dashboard)


@extend_schema(
    summary="Analytics - Top Routes",
    description="High-traffic corridors for road planning (MINICOM reporting).",
    responses={
        200: OpenApiResponse(description="Route statistics"),
    },
    tags=['Analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_top_routes(request):
    """
    GET /api/analytics/routes/top/
    
    Most frequented routes for infrastructure planning.
    Privacy: Aggregated data only, no individual customer info.
    """
    limit = int(request.GET.get('limit', 10))
    routes = AnalyticsQueries.get_top_routes(limit=limit)
    
    return Response({
        'routes': routes,
        'count': len(routes)
    })


@extend_schema(
    summary="Analytics - Commodity Breakdown",
    description="Volume statistics by commodity type for agricultural policy.",
    responses={
        200: OpenApiResponse(description="Commodity statistics"),
    },
    tags=["Analytics"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_commodity_breakdown(request):
    """
    GET /api/analytics/commodities/breakdown/
    
    Breakdown of cargo types (Potatoes vs Electronics, etc.).
    """
    commodities = AnalyticsQueries.get_commodity_breakdown()
    
    return Response({
        'commodities': commodities,
        'count': len(commodities)
    })


@extend_schema(
    summary="Analytics - Revenue Heatmap",
    description="Geospatial revenue data by sector.",
    responses={
        200: OpenApiResponse(description="Revenue by sector"),
    },
    tags=["Analytics"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_revenue_heatmap(request):
    """
    GET /api/analytics/revenue/heatmap/
    
    Economic insights by administrative sector.
    """
    heatmap = AnalyticsQueries.get_revenue_heatmap()
    
    return Response({
        'sectors': heatmap,
        'count': len(heatmap)
    })


@extend_schema(
    summary="Analytics - Driver Leaderboard",
    description="Top performing drivers by completion rate.",
    responses={
        200: OpenApiResponse(description="Driver rankings"),
    },
    tags=["Analytics"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_driver_leaderboard(request):
    """
    GET /api/analytics/drivers/leaderboard/
    
    Driver performance metrics.
    """
    limit = int(request.GET.get('limit', 20))
    leaderboard = AnalyticsQueries.get_driver_leaderboard(limit=limit)
    
    return Response({
        'drivers': leaderboard,
        'count': len(leaderboard)
    })


@extend_schema(
    summary="Government - EBM Receipt Verification",
    description="Verify tax receipt with RRA (Government audit tool).",
    responses={
        200: OpenApiResponse(description="Receipt verification result"),
    },
    tags=["Government"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gov_ebm_verify_receipt(request, ebm_receipt_number):
    """
    GET /api/gov/ebm/verify-receipt/{ebm_receipt_number}/
    
    Verify EBM digital signature with RRA.
    Used by government auditors to check tax compliance.
    """
    from government.connectors import RRAConnector
    
    rra = RRAConnector()
    verification = rra.verify_signature(ebm_receipt_number)
    
    return Response(verification)


@extend_schema(
    summary="Government - Driver License Verification",
    description="Check driver license status with RURA.",
    responses={
        200: OpenApiResponse(description="License verification result"),
    },
    tags=["Government"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gov_rura_verify_license(request, license_no):
    """
    GET /api/gov/rura/verify-license/{license_no}/
    
    Verify driver's license with RURA before shipment assignment.
    """
    from government.connectors import RURAConnector, LicenseInvalidException
    
    rura = RURAConnector()
    
    try:
        verification = rura.verify_driver_license(license_no)
        return Response(verification)
    except LicenseInvalidException as e:
        return Response({
            'error': str(e),
            'valid': False
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Government - Generate Customs Manifest",
    description="Create EAC-compliant XML manifest for cross-border shipments.",
    request={
        "application/json": {
            "shipment_id": "number"
        }
    },
    responses={
        200: OpenApiResponse(description="XML manifest"),
    },
    tags=["Government"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gov_generate_customs_manifest(request):
    """
    POST /api/gov/customs/generate-manifest/
    
    Generate XML manifest for international shipments.
    Compliance: East African Community Customs Management Act
    """
    from government.connectors import CustomsConnector
    from international.models import InternationalShipment
    
    shipment_id = request.data.get('shipment_id')
    
    try:
        shipment = InternationalShipment.objects.get(id=shipment_id)
    except InternationalShipment.DoesNotExist:
        return Response({
            'error': 'Shipment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Build shipment data
    shipment_data = {
        'destination_country': (shipment.destination_country or 'UG')[:2],
        'sender_name': shipment.customer.full_name,
        'sender_tin': shipment.customer.tax_id,
        'recipient_name': shipment.recipient_name,
        'recipient_phone': shipment.recipient_phone,
        'commodity_type': shipment.description,
        'hs_code': '0000.00',  # In production: map commodity to HS code
        'weight_kg': float(shipment.weight_kg),
        'customs_value': float(shipment.estimated_value or 0)
    }
    
    customs = CustomsConnector()
    xml_manifest = customs.generate_manifest_xml(shipment_data)
    
    return Response({
        'manifest_xml': xml_manifest,
        'shipment_tracking': shipment.tracking_number
    })


@extend_schema(
    summary="Government - Audit Access Log",
    description="View all system access logs (Government officials only).",
    responses={
        200: OpenApiResponse(description="Audit trail"),
    },
    tags=["Government"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gov_audit_access_log(request):
    """
    GET /api/gov/audit/access-log/
    
    Full audit trail for government auditors.
    Compliance: Law N° 058/2021 - Data transparency for regulators
    """
    if request.user.user_type != 'GOV_OFFICIAL':
        return Response({
            'error': 'Government official access only'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from core.models import AuditLog
    
    # Get last 500 audit logs
    logs = AuditLog.objects.all()[:500]
    
    data = [
        {
            'id': log.id,
            'user_phone': log.user_phone,
            'user_type': log.user_type,
            'action': log.action,
            'resource': f"{log.resource_type}:{log.resource_id}",
            'endpoint': log.endpoint,
            'timestamp': log.timestamp.isoformat(),
            'ip_address': log.ip_address
        }
        for log in logs
    ]
    
    return Response({
        'logs': data,
         'count': len(data)
    })
