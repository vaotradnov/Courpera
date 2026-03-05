from __future__ import annotations

import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_index_shows_admin_panel_for_staff(client, monkeypatch):
    u = User.objects.create_user(username="admin", password="pw", is_staff=True)
    assert client.login(username="admin", password="pw")
    r = client.get("/")
    assert r.status_code == 200
    txt = r.content.decode().lower()
    assert "django" in txt and "python" in txt  # admin panel shows versions


@pytest.mark.django_db
def test_index_shows_admin_panel_with_env_var(client, monkeypatch):
    monkeypatch.setenv("ADMIN_MODE", "1")
    r = client.get("/")
    assert r.status_code == 200
    txt = r.content.decode().lower()
    assert "django" in txt and "python" in txt
