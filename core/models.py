"""
Core models: User and shared location/shipment abstractions.
Includes field-level encryption for sensitive data (Law N° 058/2021).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from .encryption import EncryptedCharField


class UserManager(BaseUserManager):
    """Custom user manager for phone-based authentication."""
    
    def create_user(self, phone, password=None, **extra_fields):
        """Create and save a regular user."""
        if not phone:
            raise ValueError('Phone number is required')
        
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with Rwanda-specific fields.
    Uses phone number as the primary identifier.
    
    Compliance: Law N° 058/2021 - Data Protection and Privacy
    - Sensitive fields (national_id, tax_id) are encrypted at rest
    """
    USER_TYPE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('AGENT', 'Agent'),
        ('DRIVER', 'Driver'),
        ('ADMIN', 'Admin'),
        ('GOV_OFFICIAL', 'Government Official'),
    ]
    
    # Basic authentication
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Sensitive data - encrypted fields
    # Compliance: Law N° 058/2021 Article 22 - encryption of sensitive personal data
    nid_number = EncryptedCharField(max_length=500, blank=True, null=True, 
                                     help_text="Rwanda National ID (encrypted)")
    tax_id = EncryptedCharField(max_length=500, blank=True, null=True,
                                help_text="TIN - Tax Identification Number (encrypted)")
    
    # User metadata
    full_name = models.CharField(max_length=200, blank=True)
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES, default='CUSTOMER')
    
    # KYC & Verification - per NCSA digital identity requirements
    is_verified = models.BooleanField(default=False, 
                                      help_text="KYC verification status")
    verification_date = models.DateTimeField(null=True, blank=True,
                                            help_text="When KYC was completed")
    
    # Agent/Driver specific fields
    assigned_sector = models.CharField(max_length=100, null=True, blank=True,
                                      help_text="For Agents: assigned 416 sector")
    
    # Birth year for NID validation
    birth_year = models.IntegerField(null=True, blank=True,
                                     help_text="Year of birth for NID cross-validation")
    
    # Django admin fields
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Consent tracking for GDPR-style compliance
    terms_accepted = models.BooleanField(default=False)
    terms_version = models.CharField(max_length=10, default='1.0')
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['user_type', 'is_verified']),
            models.Index(fields=['assigned_sector']),
        ]
    
    def __str__(self) -> str:
        return f"{self.phone} ({self.user_type})"
    
    def anonymize(self) -> None:
        """
        Right to be Forgotten implementation.
        Compliance: Law N° 058/2021 Article 30 - Right to erasure
        """
        self.full_name = "REDACTED"
        self.phone = f"+250700000{self.id:04d}"  # Anonymized phone
        self.nid_number = None
        self.tax_id = None
        self.is_active = False
        self.save()


class Location(models.Model):
    """
    Rwanda administrative locations: Province > District > Sector.
    """
    LOCATION_TYPE_CHOICES = [
        ('PROVINCE', 'Province'),
        ('DISTRICT', 'District'),
        ('SECTOR', 'Sector'),
    ]
    
    name = models.CharField(max_length=100)
    location_type = models.CharField(max_length=10, choices=LOCATION_TYPE_CHOICES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    class Meta:
        db_table = 'locations'
        unique_together = ['name', 'location_type', 'parent']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name}/{self.name}"
        return self.name


class ShippingZone(models.Model):
    """
    Shipping zones for tariff calculation.
    Zone 1: Kigali, Zone 2: Provinces, Zone 3: EAC
    """
    ZONE_CHOICES = [
        ('ZONE_1', 'Kigali'),
        ('ZONE_2', 'Provinces'),
        ('ZONE_3', 'EAC Countries'),
    ]
    
    code = models.CharField(max_length=10, choices=ZONE_CHOICES, unique=True)
    name = models.CharField(max_length=50)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    per_kg_rate = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'shipping_zones'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class BaseShipment(models.Model):
    """
    Abstract base model for all shipment types.
    Contains shared fields between domestic and international shipments.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PICKED_UP', 'Picked Up'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    tracking_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_shipments')
    
    # Origin and destination
    origin = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    
    # Package details
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField()
    
    # Pricing
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tracking_number} - {self.status}"


class AuditLog(models.Model):
    """
    "Glass Log" - Audit trail for sensitive data access.
    
    Compliance: Law N° 058/2021 Article 29 - Right to access information
    Records WHO accessed WHAT data and WHEN.
    """
    ACTION_CHOICES = [
        ('VIEW', 'View'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
    ]
    
    # Who
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                            related_name='audit_logs')
    user_phone = models.CharField(max_length=20, help_text="Cached phone for deleted users")
    user_type = models.CharField(max_length=15)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # What
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50, help_text="e.g., 'shipment', 'user'")
    resource_id = models.CharField(max_length=100, help_text="ID of accessed resource")
    endpoint = models.CharField(max_length=255, help_text="API endpoint accessed")
    
    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Additional context
    request_method = models.CharField(max_length=10)  # GET, POST, etc.
    response_status = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user_phone} {self.action} {self.resource_type}:{self.resource_id} at {self.timestamp}"


class OTPVerification(models.Model):
    """
    OTP (One-Time Password) verification records.
    Simulates SMS-based identity verification for Rwanda mobile infrastructure.
    """
    PURPOSE_CHOICES = [
        ('REGISTRATION', 'Account Registration'),
        ('LOGIN', 'Login Verification'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('TRANSACTION', 'Transaction Confirmation'),
    ]
    
    phone = models.CharField(max_length=20, db_index=True)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    
    # OTP lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Attempt tracking
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    class Meta:
        db_table = 'otp_verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'is_used', 'expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"OTP for {self.phone} - {self.purpose}"
    
    def is_valid(self) -> bool:
        """Check if OTP is still valid (not expired, not used)."""
        from django.utils import timezone as tz
        return (
            not self.is_used 
            and self.expires_at > tz.now()
            and self.attempts < self.max_attempts
        )


class ShippingTariff(models.Model):
    """
    Structured tariff model for domestic shipping.
    Replaces hardcoded pricing logic.
    
    Per RURA regulations, tariffs must be transparent and auditable.
    """
    TRANSPORT_CHOICES = [
        ('MOTO', 'Motorcycle'),
        ('BUS', 'Bus'),
        ('TRUCK', 'Truck'),
    ]
    
    name = models.CharField(max_length=100, help_text="Tariff name/description")
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES)
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, 
                            related_name='tariffs')
    
    # Weight brackets
    min_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    max_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Pricing
    base_fee = models.DecimalField(max_digits=10, decimal_places=2)
    per_kg_rate = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipping_tariffs'
        ordering = ['transport_type', 'min_weight_kg']
        unique_together = ['transport_type', 'zone', 'min_weight_kg']
    
    def __str__(self) -> str:
        return f"{self.transport_type} - {self.zone.name} ({self.min_weight_kg}kg+)"
