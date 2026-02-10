"""
Domestic shipment serializers.
"""
from rest_framework import serializers
from .models import DomesticShipment, ShipmentLog
from core.validators import validate_rwanda_phone


class DomesticShipmentSerializer(serializers.ModelSerializer):
    """Serializer for domestic shipments."""
    
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    
    class Meta:
        model = DomesticShipment
        fields = [
            'id', 'tracking_number', 'customer', 'customer_phone',
            'origin', 'destination', 'transport_type',
            'weight_kg', 'description', 'cost',
            'recipient_name', 'recipient_phone', 'delivery_notes',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tracking_number', 'created_at', 'updated_at']
    
    def validate_recipient_phone(self, value):
        """Validate recipient phone format."""
        is_valid, error = validate_rwanda_phone(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
    
    def validate_weight_kg(self, value):
        """Validate weight is positive."""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value


class ShipmentLogSerializer(serializers.ModelSerializer):
    """Serializer for shipment tracking logs."""
    
    class Meta:
        model = ShipmentLog
        fields = ['id', 'status', 'location', 'notes', 'timestamp', 'updated_by']
        read_only_fields = ['id', 'timestamp']


class DomesticShipmentListSerializer(serializers.ModelSerializer):
    """Minimal serializer for list views (mobile-friendly)."""
    
    updated = serializers.SerializerMethodField()
    
    class Meta:
        model = DomesticShipment
        fields = ['tracking_number', 'status', 'destination', 'updated']
    
    def get_updated(self, obj):
        """Return humanized time since last update."""
        from django.utils.timesince import timesince
        return f"{timesince(obj.updated_at)} ago"


class StatusUpdateSerializer(serializers.Serializer):
    """Serializer for status update requests."""
    status = serializers.ChoiceField(choices=DomesticShipment.STATUS_CHOICES)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class BatchUpdateSerializer(serializers.Serializer):
    """Serializer for batch status updates."""
    tracking_numbers = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
        max_length=100
    )
    status = serializers.ChoiceField(choices=DomesticShipment.STATUS_CHOICES)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
