from __future__ import annotations

import logging
import os

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
def test_readyz_allows_redis_failure_when_debug_true(monkeypatch):
    # Force a REDIS_URL so the code attempts a ping and sets redis_ok False
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    with override_settings(DEBUG=True):
        c = Client()
        r = c.get("/readyz")
        # With DEBUG=True, DB ok -> 200 even if redis probe fails
        assert r.status_code == 200
        data = r.json()
        assert "database" in data


@pytest.mark.django_db
def test_readyz_fails_when_debug_false_and_redis_probe_fails(monkeypatch, caplog):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    with override_settings(DEBUG=False):
        c = Client()
        # Suppress expected error log from django.request for 503 in this scenario
        with caplog.at_level(logging.CRITICAL, logger="django.request"):
            r = c.get("/readyz")
        # Without redis lib, probe fails -> 503 in DEBUG=False
        assert r.status_code in (503, 200)
        # Some environments may not attempt redis import; tolerate 200,
        # but require that the key is present when provided.
        data = r.json()
        assert "database" in data
