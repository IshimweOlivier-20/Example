"""
ASGI routing configuration.
"""
from django.urls import re_path
from core.consumers import TrackingConsumer

websocket_urlpatterns = [
    re_path(r'^ws/tracking/(?P<tracking_code>[^/]+)/$', TrackingConsumer.as_asgi()),
]
