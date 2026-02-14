from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Location, ShippingZone, AuditLog, OTPVerification, ShippingTariff


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'full_name', 'user_type', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_verified', 'is_active')
    search_fields = ('phone', 'full_name', 'assigned_sector')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'nid_number', 'tax_id', 'birth_year', 'user_type', 'assigned_sector')}),
        ('Verification', {'fields': ('is_verified', 'verification_date')}),
        ('Consent', {'fields': ('terms_accepted', 'terms_version', 'terms_accepted_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'full_name', 'user_type'),
        }),
    )
    
    readonly_fields = ('verification_date', 'terms_accepted_at', 'date_joined', 'last_login')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'parent')
    list_filter = ('location_type',)
    search_fields = ('name',)


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'base_rate', 'per_kg_rate')
    list_filter = ('code',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Glass Log - Audit trail of all sensitive data access.
    Read-only for transparency and compliance.
    """
    list_display = ('timestamp', 'user_phone', 'user_type', 'action', 'resource_type', 'resource_id', 'ip_address')
    list_filter = ('action', 'user_type', 'resource_type', 'timestamp')
    search_fields = ('user_phone', 'resource_id', 'endpoint', 'ip_address')
    ordering = ('-timestamp',)
    readonly_fields = ('user', 'user_phone', 'user_type', 'ip_address', 'action', 
                      'resource_type', 'resource_id', 'endpoint', 'request_method', 
                      'response_status', 'timestamp', 'notes')
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs (compliance requirement)."""
        return False


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """OTP verification records."""
    list_display = ('phone', 'purpose', 'created_at', 'expires_at', 'is_used', 'attempts')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('phone',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'used_at')


@admin.register(ShippingTariff)
class ShippingTariffAdmin(admin.ModelAdmin):
    """Structured shipping tariffs."""
    list_display = ('name', 'transport_type', 'zone', 'min_weight_kg', 'max_weight_kg', 'base_fee', 'is_active')
    list_filter = ('transport_type', 'is_active', 'zone')
    search_fields = ('name',)
    ordering = ('transport_type', 'min_weight_kg')
