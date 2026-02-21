"""
ASGI config for ishemalink project.
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from .routing import websocket_urlpatterns
from core.ws_auth import JwtAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ishemalink.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
	'http': django_asgi_app,
	'websocket': JwtAuthMiddlewareStack(
		URLRouter(websocket_urlpatterns)
	),
})
