from django.contrib import admin
from .models import InternationalShipment, CustomsDocument


class CustomsDocumentInline(admin.TabularInline):
    model = CustomsDocument
    extra = 1


@admin.register(InternationalShipment)
class InternationalShipmentAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'customer', 'destination_country', 'status', 'created_at')
    list_filter = ('status', 'destination_country', 'created_at')
    search_fields = ('tracking_number', 'recipient_name')
    inlines = [CustomsDocumentInline]
    readonly_fields = ('tracking_number', 'created_at', 'updated_at')


@admin.register(CustomsDocument)
class CustomsDocumentAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'document_type', 'document_number', 'created_at')
    list_filter = ('document_type',)
    search_fields = ('document_number', 'shipment__tracking_number')
