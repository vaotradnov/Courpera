from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_status_text_length_validation():
    s = User.objects.create_user(username="slen", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Client()
    assert c.login(username="slen", password="pw")
    long_text = "x" * 500
    r = c.post("/api/v1/status/", {"text": long_text}, content_type="application/json")
    assert r.status_code == 400
    ok = c.post("/api/v1/status/", {"text": "ok"}, content_type="application/json")
    assert ok.status_code in (200, 201)
