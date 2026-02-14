"""
International shipment serializers.
"""
from rest_framework import serializers
from .models import InternationalShipment, CustomsDocument
from core.validators import validate_tin, validate_passport


class CustomsDocumentSerializer(serializers.ModelSerializer):
    """Serializer for customs documents."""
    
    class Meta:
        model = CustomsDocument
        fields = ['id', 'document_type', 'document_number', 'issuing_authority', 'expiry_date']
        read_only_fields = ['id']
    
    def validate(self, data):
        """Validate document based on type."""
        doc_type = data.get('document_type')
        doc_number = data.get('document_number')
        
        if doc_type == 'TIN':
            is_valid, error = validate_tin(doc_number)
            if not is_valid:
                raise serializers.ValidationError({'document_number': error})
        
        elif doc_type == 'PASSPORT':
            is_valid, error = validate_passport(doc_number)
            if not is_valid:
                raise serializers.ValidationError({'document_number': error})
        
        return data


class InternationalShipmentSerializer(serializers.ModelSerializer):
    """Serializer for international shipments."""
    
    customs_documents = CustomsDocumentSerializer(many=True, read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    
    class Meta:
        model = InternationalShipment
        fields = [
            'id', 'tracking_number', 'customer', 'customer_phone',
            'origin', 'destination', 'destination_country',
            'weight_kg', 'description', 'cost', 'estimated_value',
            'recipient_name', 'recipient_phone', 'recipient_address',
            'customs_declaration', 'customs_documents',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tracking_number', 'created_at', 'updated_at']
    
    def validate_weight_kg(self, value):
        """Validate weight is positive."""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value
    
    def validate_estimated_value(self, value):
        """Validate estimated value is positive."""
        if value <= 0:
            raise serializers.ValidationError("Estimated value must be greater than 0")
        return value


class InternationalShipmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating international shipments with nested customs documents.
    """
    customs_documents = CustomsDocumentSerializer(many=True)
    
    class Meta:
        model = InternationalShipment
        fields = [
            'origin', 'destination', 'destination_country',
            'weight_kg', 'description', 'cost', 'estimated_value',
            'recipient_name', 'recipient_phone', 'recipient_address',
            'customs_declaration', 'customs_documents'
        ]
    
    def create(self, validated_data):
        """Create shipment with nested customs documents."""
        customs_docs_data = validated_data.pop('customs_documents', [])
        
        shipment = InternationalShipment.objects.create(**validated_data)
        
        # Create customs documents
        for doc_data in customs_docs_data:
            CustomsDocument.objects.create(shipment=shipment, **doc_data)
        
        return shipment
