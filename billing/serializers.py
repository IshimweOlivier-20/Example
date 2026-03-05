"""
Billing serializers.
"""
from rest_framework import serializers
from .models import Invoice, Payment


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoices."""

    amount = serializers.DecimalField(source='total_amount', max_digits=12, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    shipment_id = serializers.IntegerField(read_only=True, allow_null=True)
    shipment_type = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'customer', 'total_amount', 'amount', 'tax_amount',
            'shipment_id', 'shipment_type', 'status', 'created_at', 'due_date', 'paid_at'
        ]
        read_only_fields = ['id', 'created_at', 'paid_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""

    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'amount', 'payment_method', 'reference_number', 'created_at']
        read_only_fields = ['id', 'created_at']
