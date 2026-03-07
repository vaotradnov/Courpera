from __future__ import annotations

import threading
from typing import Dict

from django.http import HttpRequest, HttpResponse

_lock = threading.Lock()
_counters: Dict[str, int] = {
    "courpera_notifications_created_total": 0,
    "courpera_ws_notif_push_total": 0,
}


def inc(name: str, value: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + int(value)


def metrics(request: HttpRequest) -> HttpResponse:
    lines = [
        "# HELP courpera_notifications_created_total Total chat notifications created",
        "# TYPE courpera_notifications_created_total counter",
        f"courpera_notifications_created_total {_counters.get('courpera_notifications_created_total', 0)}",
        "# HELP courpera_ws_notif_push_total Total websocket notification bumps pushed",
        "# TYPE courpera_ws_notif_push_total counter",
        f"courpera_ws_notif_push_total {_counters.get('courpera_ws_notif_push_total', 0)}",
    ]
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; version=0.0.4")
