"""
Centralized error handling and custom exceptions.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ValidationError400(APIException):
    """Return 400 Bad Request with custom message."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid input'


class Forbidden403(APIException):
    """Return 403 Forbidden."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Permission denied'


class NotFound404(APIException):
    """Return 404 Not Found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found'


class ThrottleError429(APIException):
    """Return 429 Too Many Requests."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many requests'
