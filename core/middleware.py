"""
Security and audit middleware for IshemaLink API.

Compliance: Law N° 058/2021 Article 29 - Data Controllers must maintain audit logs
of all access to personal data.
"""
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
import re

User = get_user_model()


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract client IP address from request.
    Handles proxy headers (X-Forwarded-For).
    
    Args:
        request: HTTP request object
        
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def is_sensitive_endpoint(path: str) -> bool:
    """
    Determine if an API endpoint accesses sensitive data.
    
    Sensitive endpoints include:
    - Shipment details (contains customer info, cargo value)
    - User profiles (contains NID, phone)
    - Financial/billing data
    - International shipments (contains tax IDs)
    
    Args:
        path: Request path
        
    Returns:
        Boolean indicating if endpoint is sensitive
    """
    sensitive_patterns = [
        r'/api/domestic/shipments/\d+/',
        r'/api/international/shipments/\d+/',
        r'/api/shipments/\d+/',
        r'/api/users/\d+/',
        r'/api/users/me/',
        r'/api/billing/',
        r'/api/privacy/my-data/',
        r'/api/identity/status/',
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, path):
            return True
    
    return False


def extract_resource_info(path: str) -> tuple[str, str]:
    """
    Extract resource type and ID from request path.
    
    Args:
        path: Request path (e.g., '/api/shipments/123/')
        
    Returns:
        Tuple of (resource_type, resource_id)
    """
    shipment_match = re.search(r'/api/(domestic|international)/shipments/(\d+)/', path)
    if shipment_match:
        return shipment_match.group(1), shipment_match.group(2)

    match = re.search(r'/api/(\w+)/(\d+)/', path)
    if match:
        return match.group(1), match.group(2)

    if '/users/me/' in path:
        return 'user_profile', 'me'

    return 'unknown', ''


class AuditLoggingMiddleware:
    """
    "Glass Log" Middleware - Records all access to sensitive data.
    
    Compliance: Law N° 058/2021 Article 29
    - Record WHO (user identity)
    - Record WHAT (resource accessed)
    - Record WHEN (timestamp)
    
    This implements the "Glass Log" concept where every data access is transparent
    and auditable by data owners and regulators (RURA, NCSA).
    """
    
    def __init__(self, get_response: Callable):
        """
        Initialize middleware.
        
        Args:
            get_response: Next middleware or view in chain
        """
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and log if accessing sensitive data.
        
        Args:
            request: HTTP request object
            
        Returns:
            HTTP response from view
        """
        # Store request start time for processing duration
        request._audit_start_time = timezone.now()
        
        # Process request
        response = self.get_response(request)
        
        # Log if this was a GET request to sensitive data
        # Per Law N° 058/2021: READ access must be logged, not just writes
        if request.method == 'GET' and is_sensitive_endpoint(request.path):
            self._log_access(request, response)
        
        return response
    
    def _log_access(self, request: HttpRequest, response: HttpResponse) -> None:
        """
        Create audit log entry for data access.
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        # Import here to avoid circular imports
        from core.models import AuditLog
        
        # Only log if user is authenticated
        if not request.user.is_authenticated:
            return
        
        # Extract resource information
        resource_type, resource_id = extract_resource_info(request.path)
        
        # Determine action based on method
        action_map = {
            'GET': 'VIEW',
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
        }
        action = action_map.get(request.method, 'VIEW')
        
        try:
            # Create audit log entry
            AuditLog.objects.create(
                user=request.user,
                user_phone=request.user.phone,
                user_type=request.user.user_type,
                ip_address=get_client_ip(request),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                endpoint=request.path,
                request_method=request.method,
                response_status=response.status_code,
                notes=f"Accessed by {request.user.user_type}"
            )
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log: {e}")


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.
    
    Implements OWASP security best practices:
    - HSTS (HTTP Strict Transport Security)
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    """
    
    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Add security headers to response."""
        response = self.get_response(request)
        
        # HSTS: Force HTTPS for 1 year
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # XSS Protection (legacy but still useful)
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy - Allow Swagger UI resources
        # For development, allow unsafe-inline for CSS/JS from CDN
        # In production, use nonces or specific CSP sources
        csp_header = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        response['Content-Security-Policy'] = csp_header
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


class RateLimitMetadataMiddleware:
    """
    Add rate limit information to response headers.
    Helps clients implement proper backoff strategies.
    """
    
    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Add rate limit headers if throttling was applied."""
        response = self.get_response(request)
        
        # Check if throttling info was added by DRF throttle classes
        if hasattr(request, 'throttle_metadata'):
            metadata = request.throttle_metadata
            response['X-RateLimit-Limit'] = str(metadata.get('limit', ''))
            response['X-RateLimit-Remaining'] = str(metadata.get('remaining', ''))
            response['X-RateLimit-Reset'] = str(metadata.get('reset', ''))
        
        return response
