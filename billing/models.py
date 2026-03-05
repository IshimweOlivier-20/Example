"""
Billing models for shipment costs and invoicing.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


def default_invoice_due_date():
    return (timezone.now() + timedelta(days=30)).date()


class Invoice(models.Model):
    """
    Invoice for shipment costs.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(default=default_invoice_due_date)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        amount = kwargs.pop('amount', None)
        shipment_id = kwargs.pop('shipment_id', None)
        shipment_type = kwargs.pop('shipment_type', None)
        tax_amount = kwargs.pop('tax_amount', None)

        super().__init__(*args, **kwargs)

        if amount is not None:
            self.total_amount = amount

        self._shipment_id = shipment_id
        self._shipment_type = shipment_type
        self._tax_amount = tax_amount

    def __str__(self):
        return f"Invoice {self.id} - {self.customer.phone}"

    @property
    def amount(self):
        return self.total_amount

    @amount.setter
    def amount(self, value):
        self.total_amount = value

    @property
    def shipment_id(self):
        return self._shipment_id

    @shipment_id.setter
    def shipment_id(self, value):
        self._shipment_id = value

    @property
    def shipment_type(self):
        return self._shipment_type

    @shipment_type.setter
    def shipment_type(self, value):
        self._shipment_type = value

    @property
    def tax_amount(self):
        if self._tax_amount is not None:
            return self._tax_amount

        return (self.total_amount * Decimal('0.18')).quantize(Decimal('0.01'))

    @tax_amount.setter
    def tax_amount(self, value):
        self._tax_amount = value


class Payment(models.Model):
    """
    Payment records for invoices.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='MOBILE_MONEY')
    reference_number = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.reference_number}"
