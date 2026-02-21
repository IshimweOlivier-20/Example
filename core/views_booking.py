"""
Integrated booking and payment views for IshemaLink.

Implements the Grand Integration: Shipment → Tariff → Payment → Driver Assignment
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from decimal import Decimal
import logging

from core.services import BookingService, PaymentService, NotificationService
from government.connectors import RRAConnector, RURAConnector

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Create Integrated Shipment Booking",
    description="Unified endpoint for domestic and international shipments with automatic payment initiation.",
    request={
        "application/json": {
            "shipment_type": "DOMESTIC or INTERNATIONAL",
            "origin": "string",
            "destination": "string",
            "weight_kg": "number",
            "commodity_type": "string",
            "recipient_phone": "string",
            "recipient_name": "string",
            "transport_type": "MOTO or BUS (optional)",
            "destination_country": "string (international only)",
            "recipient_address": "string (international only)",
            "customs_docs": "object (optional, for international)"
        }
    },
    responses={
        201: OpenApiResponse(description="Shipment created, payment initiated"),
        400: OpenApiResponse(description="Invalid request data"),
    },
    tags=["Booking"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_shipment(request):
    """
    POST /api/shipments/create/
    
    Create a new shipment booking and initiate payment.
    
    Workflow:
    1. Validate shipment data
    2. Calculate tariff
    3. Create shipment (status=PENDING_PAYMENT)
    4. Initiate Mobile Money payment
    5. Return payment reference for customer to confirm
    
    The shipment will only proceed to driver assignment after payment confirmation.
    """
    user = request.user
    booking_service = BookingService()
    
    # Extract data
    shipment_type = request.data.get('shipment_type')
    origin = request.data.get('origin')
    destination = request.data.get('destination')
    weight_kg = request.data.get('weight_kg')
    commodity_type = request.data.get('commodity_type')
    recipient_phone = request.data.get('recipient_phone')
    recipient_name = request.data.get('recipient_name')
    transport_type = request.data.get('transport_type')
    destination_country = request.data.get('destination_country')
    recipient_address = request.data.get('recipient_address')
    customs_docs = request.data.get('customs_docs')
    
    # Validate required fields
    if not all([shipment_type, origin, destination, weight_kg,
                commodity_type, recipient_phone, recipient_name]):
        return Response({
            'error': 'Missing required fields'
        }, status=status.HTTP_400_BAD_REQUEST)

    if shipment_type == 'INTERNATIONAL':
        if not destination_country or not recipient_address:
            return Response({
                'error': 'International shipments require destination_country and recipient_address'
            }, status=status.HTTP_400_BAD_REQUEST)
        if not customs_docs or not customs_docs.get('declaration') or customs_docs.get('estimated_value') is None:
            return Response({
                'error': 'International shipments require customs_docs with declaration and estimated_value'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        weight_kg = Decimal(str(weight_kg))
    except (ValueError, TypeError):
        return Response({
            'error': 'Invalid weight value'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create booking and initiate payment
        shipment, payment_reference = booking_service.create_booking(
            user=user,
            shipment_type=shipment_type,
            origin=origin,
            destination=destination,
            weight_kg=weight_kg,
            commodity_type=commodity_type,
            recipient_phone=recipient_phone,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            destination_country=destination_country,
            transport_type=transport_type,
            customs_docs=customs_docs
        )
        
        return Response({
            'tracking_number': shipment.tracking_number,
            'payment_reference': payment_reference,
            'total_cost': float(shipment.cost),
            'status': shipment.status,
            'message': 'Please confirm Mobile Money payment on your phone'
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Shipment creation failed: {e}")
        return Response({
            'error': 'Failed to create shipment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Initiate Mobile Money Payment",
    description="Trigger MTN/Airtel Money push prompt for shipment payment.",
    request={
        "application/json": {
            "tracking_number": "string",
            "payment_method": "MTN_MOMO or AIRTEL_MONEY"
        }
    },
    responses={
        200: OpenApiResponse(description="Payment initiated"),
        404: OpenApiResponse(description="Shipment not found"),
    },
    tags=["Payment"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """
    POST /api/payments/initiate/
    
    Initiate payment for an existing shipment.
    Customer will receive a push prompt on their phone.
    """
    tracking_number = request.data.get('tracking_number')
    payment_method = request.data.get('payment_method', 'MTN_MOMO')
    
    # Find shipment
    from domestic.models import DomesticShipment
    from international.models import InternationalShipment
    
    shipment = None
    try:
        shipment = DomesticShipment.objects.get(tracking_number=tracking_number)
    except DomesticShipment.DoesNotExist:
        try:
            shipment = InternationalShipment.objects.get(tracking_number=tracking_number)
        except InternationalShipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if already paid
    if shipment.payment_confirmed:
        return Response({
            'error': 'Payment already confirmed'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Initiate payment
    payment_service = PaymentService()
    payment_reference = payment_service.initiate_payment(
        amount=shipment.cost,
        phone=request.user.phone,
        description=f"Shipment {tracking_number}"
    )
    
    return Response({
        'payment_reference': payment_reference,
        'amount': float(shipment.cost),
        'payment_method': payment_method,
        'message': 'Check your phone to confirm payment'
    })


@extend_schema(
    summary="Payment Webhook Callback",
    description="Receive payment confirmation from Mobile Money gateway (MTN/Airtel).",
    request={
        "application/json": {
            "payment_reference": "string",
            "status": "SUCCESS or FAILED",
            "transaction_id": "string",
            "amount": "number"
        }
    },
    responses={
        200: OpenApiResponse(description="Webhook processed"),
    },
    tags=["Payment"],
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Webhook from external service
def payment_webhook(request):
    """
    POST /api/payments/webhook/
    
    Receive payment status from Mobile Money provider.
    This endpoint is called asynchronously by MTN/Airtel servers.
    
    Security: In production, verify webhook signature
    """
    payment_reference = request.data.get('payment_reference')
    payment_status = request.data.get('status')
    transaction_id = request.data.get('transaction_id')
    
    logger.info(
        f"Payment webhook received: {payment_reference} - {payment_status}"
    )
    
    # Process payment confirmation
    booking_service = BookingService()
    success = booking_service.confirm_payment(payment_reference, payment_status)
    
    if success:
        # Generate EBM receipt for successful payments
        if payment_status == 'SUCCESS':
            amount = Decimal(str(request.data.get('amount', 0)))
            tax_amount = amount * Decimal('0.18')  # 18% VAT
            
            rra = RRAConnector()
            receipt = rra.sign_receipt(
                amount=amount,
                tax_amount=tax_amount,
                transaction_id=transaction_id
            )
            
            logger.info(f"EBM receipt generated: {receipt['ebm_receipt_number']}")
        
        return Response({'status': 'processed'})
    else:
        return Response({
            'error': 'Payment reference not found'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Real-time Shipment Tracking",
    description="Get live location and status of shipment in transit.",
    responses={
        200: OpenApiResponse(description="Current location and status"),
        404: OpenApiResponse(description="Shipment not found"),
    },
    tags=["Tracking"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_shipment_live(request, tracking_code):
    """
    GET /api/tracking/{tracking_code}/live/
    
    Real-time tracking endpoint for mobile apps.
    Returns current GPS coordinates (if driver is active) and status.
    
    In production: Integrate with GPS tracker or driver mobile app
    """
    from domestic.models import DomesticShipment
    from international.models import InternationalShipment
    
    # Find shipment
    shipment = None
    try:
        shipment = DomesticShipment.objects.select_related('driver').get(
            tracking_number=tracking_code
        )
    except DomesticShipment.DoesNotExist:
        try:
            shipment = InternationalShipment.objects.select_related('driver').get(
                tracking_number=tracking_code
            )
        except InternationalShipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Check authorization (only customer or driver can track)
    if request.user != shipment.customer and request.user != shipment.driver:
        return Response({
            'error': 'Not authorized to track this shipment'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Mock GPS coordinates
    # In production: Fetch from driver's mobile app or GPS device
    tracking_data = {
        'tracking_number': shipment.tracking_number,
        'status': shipment.status,
        'origin': shipment.origin,
        'destination': shipment.destination,
        'current_location': {
            'latitude': -1.9536,  # Mock: Kigali coordinates
            'longitude': 30.0606,
            'address': 'Kigali, Rwanda',
            'last_updated': '2026-02-20T10:30:00Z'
        },
        'driver': {
            'name': shipment.driver.full_name if shipment.driver else None,
            'phone': shipment.driver.phone if shipment.driver else None
        } if shipment.driver else None,
        'estimated_delivery': None,  # Calculate based on distance & traffic
        'history': []  # Previous location checkpoints
    }
    
    return Response(tracking_data)


@extend_schema(
    summary="Broadcast Emergency Alert",
    description="Send emergency notification to all drivers (Admin only).",
    request={
        "application/json": {
            "message": "string",
            "target_group": "ALL_DRIVERS, DRIVERS_IN_SECTOR, etc."
        }
    },
    responses={
        200: OpenApiResponse(description="Alert sent"),
    },
    tags=["Notifications"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def broadcast_notification(request):
    """
    POST /api/notifications/broadcast/
    
    Admin endpoint to send emergency alerts.
    Use case: "All drivers: Road closed in Nyamagabe due to landslide"
    """
    if request.user.user_type != 'ADMIN':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    message = request.data.get('message')
    target_group = request.data.get('target_group', 'DRIVER')
    
    notification_service = NotificationService()
    count = notification_service.broadcast_alert(target_group, message)
    
    return Response({
        'message': 'Alert sent',
        'recipients': count
    })
