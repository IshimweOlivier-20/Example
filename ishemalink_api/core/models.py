"""
Core models: User and shared location/shipment abstractions.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


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
    """
    USER_TYPE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('AGENT', 'Agent'),
        ('ADMIN', 'Admin'),
    ]
    
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    national_id = models.CharField(max_length=16, unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='CUSTOMER')
    
    # Agent-specific field
    assigned_sector = models.CharField(max_length=100, null=True, blank=True)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    
    # Django admin fields
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.phone} ({self.user_type})"


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
