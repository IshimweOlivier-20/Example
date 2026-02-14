"""
Shared shipment views for manifest and tracking endpoints.
"""
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from domestic.models import DomesticShipment
from international.models import InternationalShipment


@api_view(['GET'])
def unified_tracking_list(request):
    """
    GET /api/shipments/?page=1&size=20
    Unified list of both domestic and international shipments.
    Supports filtering by status, destination, and search by tracking_number.
    """
    # This endpoint is handled by individual app viewsets,
    # but kept here for reference to the unified concept.
    return Response({
        'message': 'Use /api/domestic/shipments/ or /api/international/shipments/'
    })
