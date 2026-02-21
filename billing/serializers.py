"""
Billing serializers.
"""
from rest_framework import serializers
from .models import Invoice, Payment


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoices."""

    class Meta:
        model = Invoice
        fields = ['id', 'customer', 'total_amount', 'status', 'created_at', 'due_date', 'paid_at']
        read_only_fields = ['id', 'created_at', 'paid_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""

    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'amount', 'payment_method', 'reference_number', 'created_at']
        read_only_fields = ['id', 'created_at']
