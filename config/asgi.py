"""ASGI entrypoint for Courpera (HTTP and WebSocket).

This file deliberately performs minimal dynamic importing and uses a
deterministic websocket dispatcher so tests/dev do not depend on URL
resolvers when matching websocket paths.
"""

from __future__ import annotations

import os
import re
from typing import Any

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application
from django.urls import path

# Default to development settings for local runs; override in deployment.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

# Export canonical websocket_urlpatterns for tooling/documentation
websocket_urlpatterns = []  # type: ignore[var-annotated]
try:
    from messaging.consumers import CourseChatConsumer as _CCC
    from messaging.consumers import RoomConsumer as _RC

    websocket_urlpatterns = [
        path("ws/chat/course/<int:course_id>/", _CCC.as_asgi()),
        path("ws/chat/room/<int:room_id>/", _RC.as_asgi()),
    ]
except Exception:  # pragma: no cover
    # If consumers cannot import during tooling, leave patterns empty.
    pass


# Deterministic dispatcher used by the ASGI app
_re_course = re.compile(r"^/ws/chat/course/(?P<course_id>\d+)/$")
_re_room = re.compile(r"^/ws/chat/room/(?P<room_id>\d+)/$")


async def _chat_dispatch(scope: dict[str, Any], receive, send):  # pragma: no cover
    # Import inside function to avoid import-order issues during collection.
    from messaging.consumers import CourseChatConsumer as _CCC
    from messaging.consumers import RoomConsumer as _RC

    path = scope.get("path", "") or ""
    m = _re_course.match(path)
    if m:
        kwargs = {"course_id": int(m.group("course_id"))}
        app = _CCC.as_asgi()
        return await app(dict(scope, url_route={"args": (), "kwargs": kwargs}), receive, send)
    m = _re_room.match(path)
    if m:
        kwargs = {"room_id": int(m.group("room_id"))}
        app = _RC.as_asgi()
        return await app(dict(scope, url_route={"args": (), "kwargs": kwargs}), receive, send)
    await send({"type": "websocket.close", "code": 4004})


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(_chat_dispatch),
    }
)
