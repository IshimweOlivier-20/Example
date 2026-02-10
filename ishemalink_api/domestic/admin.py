from django.contrib import admin
from .models import DomesticShipment, ShipmentLog


@admin.register(DomesticShipment)
class DomesticShipmentAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'customer', 'status', 'origin', 'destination', 'created_at')
    list_filter = ('status', 'transport_type', 'created_at')
    search_fields = ('tracking_number', 'recipient_name', 'recipient_phone')
    readonly_fields = ('tracking_number', 'created_at', 'updated_at')


@admin.register(ShipmentLog)
class ShipmentLogAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'status', 'location', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('shipment__tracking_number',)
