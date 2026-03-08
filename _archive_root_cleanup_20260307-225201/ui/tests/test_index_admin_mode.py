from __future__ import annotations

import os

import pytest


@pytest.mark.django_db
def test_index_shows_admin_mode_panel(client, monkeypatch):
    # Force Admin Mode to exercise runinfo and links rendering
    monkeypatch.setenv("ADMIN_MODE", "1")
    r = client.get("/")
    assert r.status_code == 200
    txt = r.text
    assert "Environment" in txt
    assert "Swagger UI" in txt
