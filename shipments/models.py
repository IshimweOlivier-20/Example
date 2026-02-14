"""
Shared shipment models for cross-app tracking.
"""
from django.db import models


class ShipmentManifest(models.Model):
    """
    Manifest for bulk shipment tracking at hubs.
    Aggregates multiple shipments for agent visibility.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    hub_location = models.CharField(max_length=200)
    total_shipments = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'shipment_manifests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Manifest {self.id} - {self.hub_location}"
