from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_teacher_cannot_create_status_and_list_empty():
    t = User.objects.create_user(username="tstatus", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])

    c = Client()
    assert c.login(username="tstatus", password="pw")
    r = c.post("/api/v1/status/", {"text": "hello"}, content_type="application/json")
    assert r.status_code == 403
    # Teachers get an empty list by design
    r2 = c.get("/api/v1/status/")
    assert r2.status_code == 200
    assert r2.json().get("count", 0) == 0
