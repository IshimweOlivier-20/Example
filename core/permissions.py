"""
Permissions for role-based access control.

Compliance: Implements RBAC per NCSA cybersecurity framework.
Granular permissions based on user role and data ownership.
"""
from rest_framework import permissions
from typing import Any


class IsAgent(permissions.BasePermission):
    """Permission class for Agent users."""
    
    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.user_type == 'AGENT'


class IsCustomer(permissions.BasePermission):
    """Permission class for Customer users."""
    
    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.user_type == 'CUSTOMER'


class IsAdmin(permissions.BasePermission):
    """Permission class for Admin users."""
    
    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.user_type == 'ADMIN'


class IsSectorAgent(permissions.BasePermission):
    """
    Restrict Agents to only access shipments within their assigned sector.
    
    Implements geographic access control per Rwanda's 416 administrative sectors.
    Prevents agents from accessing data outside their jurisdiction.
    """
    
    def has_permission(self, request, view) -> bool:
        """Check if user is an agent."""
        return (
            request.user.is_authenticated 
            and request.user.user_type == 'AGENT'
            and request.user.assigned_sector is not None
        )
    
    def has_object_permission(self, request, view, obj: Any) -> bool:
        """
        Check if agent can access this specific shipment.
        
        Args:
            request: HTTP request
            view: View being accessed
            obj: Shipment object
            
        Returns:
            Boolean indicating permission
        """
        # Admin bypass
        if request.user.user_type == 'ADMIN':
            return True
        
        # Agent must be assigned to sector
        if not request.user.assigned_sector:
            return False
        
        # Check if shipment origin or destination is in agent's sector
        # This is a simplified check - in production, use Location model
        agent_sector = request.user.assigned_sector.lower()
        
        origin = getattr(obj, 'origin', '').lower()
        destination = getattr(obj, 'destination', '').lower()
        
        return agent_sector in origin or agent_sector in destination


class IsGovOfficial(permissions.BasePermission):
    """
    Government officials (RURA, RRA, NCSA) have READ-ONLY access to all data.
    
    Compliance: Law N° 058/2021 Article 50 - Data Controller obligations
    to provide data access to regulatory authorities.
    """
    
    def has_permission(self, request, view) -> bool:
        """Check if user is a government official."""
        return (
            request.user.is_authenticated 
            and request.user.user_type == 'GOV_OFFICIAL'
        )
    
    def has_object_permission(self, request, view, obj: Any) -> bool:
        """Government officials can view all objects."""
        # Read-only access
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # No write access
        return False


class IsDriver(permissions.BasePermission):
    """
    Drivers can only see delivery information, NOT pricing/financial details.
    
    Business logic: Drivers need to know WHERE to deliver, not HOW MUCH it costs.
    """
    
    def has_permission(self, request, view) -> bool:
        """Check if user is a driver."""
        return request.user.is_authenticated and request.user.user_type == 'DRIVER'
    
    def has_object_permission(self, request, view, obj: Any) -> bool:
        """
        Drivers can only access shipments assigned to them.
        
        Note: This requires a driver field on shipment models.
        """
        # Check if driver is assigned to this shipment
        if hasattr(obj, 'driver') and obj.driver == request.user:
            return True
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission: Only owner can modify, others can read (if authenticated).
    """
    
    def has_object_permission(self, request, view, obj: Any) -> bool:
        """
        Read permissions to authenticated users.
        Write permissions only to owner.
        
        Args:
            request: HTTP request
            view: View being accessed
            obj: Object being accessed
            
        Returns:
            Boolean indicating permission
        """
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for owner
        # Handle different object types
        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Default to admin-only write
        return request.user.user_type == 'ADMIN'


class IsVerified(permissions.BasePermission):
    """
    Require KYC verification for certain actions.
    
    Prevent unverified users from creating shipments or accessing sensitive features.
    Compliance: Anti-fraud measures per RURA requirements.
    """
    
    message = 'You must complete identity verification (KYC) to perform this action.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user is verified."""
        return (
            request.user.is_authenticated 
            and request.user.is_verified
        )


class ReadOnlyPermission(permissions.BasePermission):
    """
    Read-only access for specific user types.
    Used for government/audit views.
    """
    
    def has_permission(self, request, view) -> bool:
        """Only allow safe methods."""
        return request.method in permissions.SAFE_METHODS

