"""
International shipment views.
"""
from rest_framework import generics, filters, viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import InternationalShipment, CustomsDocument
from .serializers import (
    InternationalShipmentSerializer, 
    InternationalShipmentCreateSerializer,
    CustomsDocumentSerializer
)


class InternationalShipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for international shipments.
    """
    queryset = InternationalShipment.objects.all()
    serializer_class = InternationalShipmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'destination_country']
    search_fields = ['tracking_number', 'recipient_name']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InternationalShipmentCreateSerializer
        return InternationalShipmentSerializer
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class InternationalShipmentListCreateView(generics.ListCreateAPIView):
    """
    GET /api/international/shipments/ - List international shipments
    POST /api/international/shipments/ - Create new international shipment
    """
    queryset = InternationalShipment.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'destination_country']
    search_fields = ['tracking_number', 'recipient_name']
    
    def get_serializer_class(self):
        """Use create serializer for POST requests."""
        if self.request.method == 'POST':
            return InternationalShipmentCreateSerializer
        return InternationalShipmentSerializer
    
    def perform_create(self, serializer):
        """Set customer to current user."""
        serializer.save(customer=self.request.user)


class InternationalShipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/international/shipments/{id}/
    """
    queryset = InternationalShipment.objects.all()
    serializer_class = InternationalShipmentSerializer
    permission_classes = [IsAuthenticated]


class CustomsDocumentCreateView(generics.CreateAPIView):
    """
    POST /api/international/customs-documents/
    Add customs document to existing shipment.
    """
    queryset = CustomsDocument.objects.all()
    serializer_class = CustomsDocumentSerializer
    permission_classes = [IsAuthenticated]
