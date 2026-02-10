"""
ASGI config for ishemalink project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ishemalink.settings')

application = get_asgi_application()
