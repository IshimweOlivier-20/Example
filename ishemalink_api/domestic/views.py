"""
Domestic shipment views with async support for notifications.
"""
import asyncio
import logging
import uuid
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import DomesticShipment, ShipmentLog
from .serializers import (
    DomesticShipmentSerializer, 
    DomesticShipmentListSerializer,
    ShipmentLogSerializer,
    StatusUpdateSerializer,
    BatchUpdateSerializer
)

logger = logging.getLogger('async_tasks')


# Async notification mock
async def mock_sms_gateway(phone: str, message: str) -> bool:
    """
    Mock SMS gateway with artificial latency.
    Simulates external API call.
    """
    await asyncio.sleep(2)  # Simulate 2-second API response
    
    # Random failure rate (10%)
    import random
    if random.random() < 0.1:
        logger.error(f"[MOCK SMS] Failed to send to {phone}")
        raise Exception("SMS gateway timeout")
    
    logger.info(f"[MOCK SMS] Sent to {phone}: {message}")
    return True


async def send_notification(phone: str, tracking_number: str, new_status: str) -> None:
    """
    Send notification asynchronously.
    """
    try:
        message = f"IshemaLink: Your shipment {tracking_number} is now {new_status}"
        await mock_sms_gateway(phone, message)
    except Exception as e:
        logger.error(f"Notification failed for {tracking_number}: {e}")


class DomesticShipmentListCreateView(generics.ListCreateAPIView):
    """
    GET /api/domestic/shipments/ - List shipments with pagination/filtering
    POST /api/domestic/shipments/ - Create new domestic shipment
    """
    queryset = DomesticShipment.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'destination', 'transport_type']
    search_fields = ['tracking_number', 'recipient_name', 'recipient_phone']
    ordering_fields = ['created_at', 'updated_at']
    
    def get_serializer_class(self):
        """Use minimal serializer for list view."""
        if self.request.method == 'GET':
            return DomesticShipmentListSerializer
        return DomesticShipmentSerializer
    
    def perform_create(self, serializer):
        """Set customer to current user."""
        serializer.save(customer=self.request.user)


class DomesticShipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/domestic/shipments/{id}/
    """
    queryset = DomesticShipment.objects.all()
    serializer_class = DomesticShipmentSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
async def update_shipment_status(request, pk):
    """
    POST /api/shipments/{id}/update-status/
    Async status update with notification.
    """
    try:
        # Fetch shipment (sync operation wrapped for async)
        shipment = await sync_to_async(get_object_or_404)(DomesticShipment, pk=pk)
        
        serializer = StatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        new_status = serializer.validated_data['status']
        location = serializer.validated_data.get('location', '')
        notes = serializer.validated_data.get('notes', '')
        
        # Update shipment status
        shipment.status = new_status
        await sync_to_async(shipment.save)()
        
        # Create log entry
        await sync_to_async(ShipmentLog.objects.create)(
            shipment=shipment,
            status=new_status,
            location=location,
            notes=notes
        )
        
        # Send notification asynchronously (fire and forget)
        customer_phone = await sync_to_async(lambda: shipment.customer.phone)()
        asyncio.create_task(
            send_notification(customer_phone, shipment.tracking_number, new_status)
        )
        
        return Response({
            'tracking_number': shipment.tracking_number,
            'status': shipment.status,
            'message': 'Status updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Status update failed for shipment {pk}: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
async def batch_update_status(request):
    """
    POST /api/shipments/batch-update/
    Bulk async status updates with error handling.
    """
    serializer = BatchUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    tracking_numbers = serializer.validated_data['tracking_numbers']
    new_status = serializer.validated_data['status']
    location = serializer.validated_data.get('location', '')
    
    # Generate task ID
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # Start background processing
    asyncio.create_task(
        process_batch_updates(tracking_numbers, new_status, location, task_id)
    )
    
    return Response({
        'message': f'Processing started for {len(tracking_numbers)} shipments.',
        'task_id': task_id,
        'status': 'queued'
    })


async def process_batch_updates(tracking_numbers: list, new_status: str, location: str, task_id: str):
    """
    Process batch updates asynchronously.
    Continues even if individual updates fail.
    """
    logger.info(f"[{task_id}] Starting batch update for {len(tracking_numbers)} shipments")
    
    success_count = 0
    fail_count = 0
    
    for tn in tracking_numbers:
        try:
            # Fetch shipment
            shipment = await sync_to_async(
                DomesticShipment.objects.filter(tracking_number=tn).first
            )()
            
            if not shipment:
                logger.warning(f"[{task_id}] Shipment {tn} not found")
                fail_count += 1
                continue
            
            # Update status
            shipment.status = new_status
            await sync_to_async(shipment.save)()
            
            # Create log
            await sync_to_async(ShipmentLog.objects.create)(
                shipment=shipment,
                status=new_status,
                location=location
            )
            
            # Send notification
            customer_phone = await sync_to_async(lambda: shipment.customer.phone)()
            try:
                await send_notification(customer_phone, tn, new_status)
            except Exception as e:
                logger.error(f"[{task_id}] Notification failed for {tn}: {e}")
            
            success_count += 1
            logger.info(f"[{task_id}] Updated {tn} successfully")
            
        except Exception as e:
            logger.error(f"[{task_id}] Failed to update {tn}: {e}")
            fail_count += 1
            continue  # Continue with next shipment
    
    logger.info(f"[{task_id}] Batch complete: {success_count} success, {fail_count} failed")


@api_view(['GET'])
def get_tracking_history(request, pk):
    """
    GET /api/shipments/{id}/tracking/
    Get full tracking history for a shipment.
    """
    shipment = get_object_or_404(DomesticShipment, pk=pk)
    logs = ShipmentLog.objects.filter(shipment=shipment)
    
    serializer = ShipmentLogSerializer(logs, many=True)
    
    return Response({
        'tracking_number': shipment.tracking_number,
        'current_status': shipment.status,
        'history': serializer.data
    })
