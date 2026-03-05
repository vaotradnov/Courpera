from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, override_settings


@pytest.mark.django_db
@pytest.mark.security
@override_settings(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=True)
def test_session_cookie_flags_secure_lax_httponly_on_login_response():
    u = User.objects.create_user(username="cook", password="pw")
    c = Client()
    r = c.post("/accounts/login/", {"username": "cook", "password": "pw"})
    # Expect redirect on successful login
    assert r.status_code in (302, 301)
    name = settings.SESSION_COOKIE_NAME
    morsel = c.cookies.get(name)
    assert morsel is not None
    assert bool(morsel["httponly"]) is True
    assert (morsel["samesite"] or "").lower() == "lax"
    assert bool(morsel["secure"]) is True


@pytest.mark.django_db
@pytest.mark.security
@override_settings(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=False)
def test_session_cookie_flags_lax_without_secure_when_not_forced():
    u = User.objects.create_user(username="cook2", password="pw")
    c = Client()
    r = c.post("/accounts/login/", {"username": "cook2", "password": "pw"})
    assert r.status_code in (302, 301)
    name = settings.SESSION_COOKIE_NAME
    morsel = c.cookies.get(name)
    assert morsel is not None
    assert bool(morsel["httponly"]) is True
    assert (morsel["samesite"] or "").lower() == "lax"
    assert bool(morsel["secure"]) is False
