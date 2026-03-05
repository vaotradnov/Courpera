from __future__ import annotations

from django.urls import reverse


def test_404_page(client):
    r = client.get("/nonexistent-404-page/")
    assert r.status_code == 404
    # Basic body smoke check
    assert "<!doctype html" in r.content.decode().lower()


def test_403_on_teacher_only_page_when_anonymous(client):
    r = client.get(reverse("accounts:home-teacher"))
    # Django redirects to login for @login_required; following redirect would show login
    assert r.status_code in (302, 403)
