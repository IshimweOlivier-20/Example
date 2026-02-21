from django.contrib import admin
from .models import ShipmentManifest


@admin.register(ShipmentManifest)
class ShipmentManifestAdmin(admin.ModelAdmin):
    list_display = ['id', 'hub_location', 'total_shipments', 'created_at']
    search_fields = ['hub_location', 'notes']
