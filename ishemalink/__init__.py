"""
Django initialization.
"""
# Optional Celery integration - only import if installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
