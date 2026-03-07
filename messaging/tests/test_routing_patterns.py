from __future__ import annotations

from messaging import routing


def test_websocket_routing_contains_expected_patterns():
    pats = routing.websocket_urlpatterns
    routes = [getattr(p.pattern, "_route", "") for p in pats]
    assert "ws/chat/course/<int:course_id>/" in routes
    assert "ws/chat/room/<int:room_id>/" in routes
    assert "ws/notify/" in routes
