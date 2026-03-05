from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_teacher_search_is_case_insensitive_and_partial():
    t = User.objects.create_user(username="tsearch", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    u1 = User.objects.create_user(username="Alice", email="alice@example.com")
    u2 = User.objects.create_user(username="bob", email="bob@example.com")

    c = Client()
    assert c.login(username="tsearch", password="pw")
    # lowercase partial matches uppercase username
    r = c.get("/accounts/search/?q=ali")
    assert r.status_code == 200
    body = r.content.decode("utf-8", errors="ignore").lower()
    assert "alice" in body
    # e-mail partial works
    r2 = c.get("/accounts/search/?q=example.com")
    assert r2.status_code == 200
    txt = r2.content.decode("utf-8", errors="ignore").lower()
    assert "alice" in txt and "bob" in txt
