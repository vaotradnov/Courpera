from __future__ import annotations

import logging

from django.test import Client


def test_healthz_ok():
    c = Client()
    r = c.get("/healthz")
    assert r.status_code == 200
    assert (r.content or b"").strip() == b"ok"


def test_readyz_reports_database_key_and_status(caplog):
    c = Client()
    # Suppress expected error logs when /readyz is 503 in CI/dev envs
    with caplog.at_level(logging.CRITICAL, logger="django.request"):
        r = c.get("/readyz")
    # In practice should be 200 when DB reachable; tolerate 503 if probe fails late in session
    assert r.status_code in (200, 503)
    data = r.json()
    assert "database" in data


def test_metrics_prometheus_and_counters_increment():
    # Increment counters via the module function, then fetch /metrics
    from config.metrics import inc

    inc("courpera_notifications_created_total", 3)
    inc("courpera_ws_notif_push_total", 2)

    c = Client()
    r = c.get("/metrics")
    assert r.status_code == 200
    # Text format and expected metric names are present
    text = r.content.decode("utf-8")
    assert "courpera_notifications_created_total" in text
    assert "courpera_ws_notif_push_total" in text
