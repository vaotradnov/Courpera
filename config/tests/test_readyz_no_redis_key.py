from __future__ import annotations

import logging
import os

from django.test import Client


def test_readyz_omits_redis_key_when_not_configured(monkeypatch, caplog):
    # Ensure REDIS_URL is not set
    try:
        monkeypatch.delenv("REDIS_URL")
    except Exception:
        pass
    c = Client()
    with caplog.at_level(logging.CRITICAL, logger="django.request"):
        r = c.get("/readyz")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "database" in data
    assert "redis" not in data
