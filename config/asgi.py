"""ASGI entrypoint for Courpera (HTTP and WebSocket)."""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Default to development settings for local runs; override in deployment.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

try:
    from messaging.routing import websocket_urlpatterns
except Exception:  # pragma: no cover
    websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
