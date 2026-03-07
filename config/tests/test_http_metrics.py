from __future__ import annotations

from django.test import Client


def test_http_response_metrics_buckets_increment():
    c = Client()
    # One 2xx and one 4xx
    assert c.get("/healthz").status_code == 200
    assert c.get("/__not_found__").status_code == 404

    r = c.get("/metrics")
    assert r.status_code == 200
    text = r.content.decode("utf-8")
    assert "courpera_http_responses_total_2xx" in text
    assert "courpera_http_responses_total_4xx" in text


def test_http_response_metrics_includes_3xx_redirect():
    c = Client()
    # Django auth logout usually redirects (3xx)
    r = c.get("/accounts/logout/")
    assert 300 <= r.status_code < 400
    metrics = c.get("/metrics").content.decode("utf-8")
    assert "courpera_http_responses_total_3xx" in metrics
