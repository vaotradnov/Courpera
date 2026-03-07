from __future__ import annotations

import threading
from typing import Dict

from django.http import HttpRequest, HttpResponse

_lock = threading.Lock()
_counters: Dict[str, int] = {
    "courpera_notifications_created_total": 0,
    "courpera_ws_notif_push_total": 0,
    # Optional additional counter for created chat messages (incremented on notify path)
    "courpera_messages_created_total": 0,
    # HTTP response status buckets
    "courpera_http_responses_total_2xx": 0,
    "courpera_http_responses_total_3xx": 0,
    "courpera_http_responses_total_4xx": 0,
    "courpera_http_responses_total_5xx": 0,
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
        "# HELP courpera_messages_created_total Total chat messages created (published)",
        "# TYPE courpera_messages_created_total counter",
        f"courpera_messages_created_total {_counters.get('courpera_messages_created_total', 0)}",
        "# HELP courpera_http_responses_total_2xx Total HTTP 2xx responses",
        "# TYPE courpera_http_responses_total_2xx counter",
        f"courpera_http_responses_total_2xx {_counters.get('courpera_http_responses_total_2xx', 0)}",
        "# HELP courpera_http_responses_total_3xx Total HTTP 3xx responses",
        "# TYPE courpera_http_responses_total_3xx counter",
        f"courpera_http_responses_total_3xx {_counters.get('courpera_http_responses_total_3xx', 0)}",
        "# HELP courpera_http_responses_total_4xx Total HTTP 4xx responses",
        "# TYPE courpera_http_responses_total_4xx counter",
        f"courpera_http_responses_total_4xx {_counters.get('courpera_http_responses_total_4xx', 0)}",
        "# HELP courpera_http_responses_total_5xx Total HTTP 5xx responses",
        "# TYPE courpera_http_responses_total_5xx counter",
        f"courpera_http_responses_total_5xx {_counters.get('courpera_http_responses_total_5xx', 0)}",
    ]
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; version=0.0.4")
