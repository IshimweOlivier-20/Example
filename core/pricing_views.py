"""
Pricing and caching views.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ShippingZone
from core.pricing import get_cached_tariffs, calculate_shipping_cost, clear_tariff_cache


@api_view(['GET'])
@permission_classes([AllowAny])
def get_tariffs(request):
    """
    GET /api/pricing/tariffs/
    Get all shipping tariffs (cached).
    """
    zones = ['ZONE_1', 'ZONE_2', 'ZONE_3']
    tariffs = {}
    cache_hit = True

    for zone_code in zones:
        tariff = get_cached_tariffs(zone_code)
        if tariff:
            tariffs[zone_code] = tariff
            if not tariff.get('cache_hit', False):
                cache_hit = False

    response_data = {
        'cached_at': timezone.now().isoformat(),
        'rates': tariffs
    }

    response = Response(response_data)

    response['X-Cache-Hit'] = 'TRUE' if cache_hit else 'FALSE'
    response['Cache-Control'] = 'public, max-age=3600'

    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_cost(request):
    """
    POST /api/pricing/calculate/
    Calculate shipping cost for specific weight and destination.
    """
    destination = request.data.get('destination')
    weight_kg = request.data.get('weight_kg')

    if not destination or not weight_kg:
        return Response({
            'error': 'Both destination and weight_kg are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        weight = Decimal(str(weight_kg))
        if weight <= 0:
            return Response({
                'error': 'Weight must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)

        cost_breakdown = calculate_shipping_cost(destination, weight)

        response = Response(cost_breakdown)
        response['X-Cache-Hit'] = 'TRUE' if cost_breakdown.get('cache_hit') else 'FALSE'

        return response

    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_cache(request):
    """
    POST /api/admin/cache/clear-tariffs/
    Force cache refresh (admin only).
    """
    cleared = clear_tariff_cache()

    return Response({
        'message': f'Tariff cache cleared for {cleared} zones',
        'timestamp': timezone.now().isoformat()
    })


class CalculateShippingCostView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return calculate_cost(request)


class ListShippingZonesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        zones = ShippingZone.objects.all().order_by('code')
        data = [
            {
                'code': zone.code,
                'name': zone.name,
                'base_rate': str(zone.base_rate),
                'per_kg_rate': str(zone.per_kg_rate),
            }
            for zone in zones
        ]
        return Response(data, status=status.HTTP_200_OK)
