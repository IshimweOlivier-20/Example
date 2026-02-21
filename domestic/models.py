"""
Domestic shipment models for local Rwanda deliveries.
"""
import uuid
from django.db import models
from core.models import BaseShipment


class DomesticShipment(BaseShipment):
    """
    Domestic shipment model for Rwanda local deliveries.
    Moto/Bus transport within Rwanda borders.
    """
    TRANSPORT_TYPE_CHOICES = [
        ('MOTO', 'Motorcycle'),
        ('BUS', 'Bus'),
    ]
    
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_TYPE_CHOICES, default='MOTO')
    
    # Recipient contact info
    recipient_name = models.CharField(max_length=200)
    recipient_phone = models.CharField(max_length=20)
    
    # Delivery notes
    delivery_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'domestic_shipments'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Generate tracking number if not set."""
        if not self.tracking_number:
            self.tracking_number = f"RW-D-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class ShipmentLog(models.Model):
    """
    Tracking log for shipment status updates.
    Records every status change with timestamp.
    """
    shipment = models.ForeignKey(
        DomesticShipment, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    status = models.CharField(max_length=20)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'shipment_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status} at {self.timestamp}"
