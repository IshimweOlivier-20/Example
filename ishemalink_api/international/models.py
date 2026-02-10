"""
International shipment models for cross-border EAC deliveries.
"""
import uuid
from django.db import models
from core.models import BaseShipment


class InternationalShipment(BaseShipment):
    """
    International shipment model for EAC cross-border deliveries.
    Requires additional customs documentation.
    """
    # Extended status choices for international
    STATUS_CHOICES = BaseShipment.STATUS_CHOICES + [
        ('AT_CUSTOMS', 'At Customs'),
        ('CLEARED_CUSTOMS', 'Cleared Customs'),
    ]
    
    DESTINATION_COUNTRY_CHOICES = [
        ('UGANDA', 'Uganda'),
        ('KENYA', 'Kenya'),
        ('DRC', 'Democratic Republic of Congo'),
        ('TANZANIA', 'Tanzania'),
        ('BURUNDI', 'Burundi'),
    ]
    
    destination_country = models.CharField(max_length=20, choices=DESTINATION_COUNTRY_CHOICES)
    
    # Recipient information
    recipient_name = models.CharField(max_length=200)
    recipient_phone = models.CharField(max_length=20)
    recipient_address = models.TextField()
    
    # Customs information
    customs_declaration = models.TextField()
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Override status to include customs statuses
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    class Meta:
        db_table = 'international_shipments'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Generate tracking number if not set."""
        if not self.tracking_number:
            country_code = self.destination_country[:2] if self.destination_country else 'XX'
            self.tracking_number = f"RW-{country_code}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class CustomsDocument(models.Model):
    """
    Customs documentation for international shipments.
    """
    DOCUMENT_TYPE_CHOICES = [
        ('PASSPORT', 'Passport'),
        ('TIN', 'Tax Identification Number'),
        ('INVOICE', 'Commercial Invoice'),
        ('CERTIFICATE', 'Certificate of Origin'),
    ]
    
    shipment = models.ForeignKey(
        InternationalShipment, 
        on_delete=models.CASCADE, 
        related_name='customs_documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=100)
    issuing_authority = models.CharField(max_length=200, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customs_documents'
    
    def __str__(self):
        return f"{self.document_type} - {self.document_number}"
