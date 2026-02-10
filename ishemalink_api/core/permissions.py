"""
Permissions for role-based access control.
"""
from rest_framework import permissions


class IsAgent(permissions.BasePermission):
    """Permission class for Agent users."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'AGENT'


class IsCustomer(permissions.BasePermission):
    """Permission class for Customer users."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'CUSTOMER'


class IsAdmin(permissions.BasePermission):
    """Permission class for Admin users."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'ADMIN'
