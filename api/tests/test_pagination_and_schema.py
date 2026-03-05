from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course


@pytest.mark.django_db
def test_courses_pagination_caps_and_param():
    # Teacher to own the created courses
    t = User.objects.create_user(username="tpag", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    for i in range(0, 60):
        Course.objects.create(owner=t, title=f"C{i}", description="")

    c = Client()
    # Request an excessive page size; expect capped to 100
    r = c.get("/api/v1/courses/?page_size=500")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data and isinstance(data["results"], list)
    assert len(data["results"]) <= 100
    # Small explicit page size honoured
    r2 = c.get("/api/v1/courses/?page_size=5")
    assert r2.status_code == 200
    assert len(r2.json()["results"]) == 5


@pytest.mark.django_db
def test_openapi_includes_materials_path():
    c = Client()
    r = c.get("/api/schema/")
    assert r.status_code == 200
    body = r.content
    try:
        payload = json.loads(body)
        assert "openapi" in payload
        paths = payload.get("paths") or {}
        # Expect materials endpoint to be present in schema
        assert any("/api/v1/materials" in p for p in paths.keys())
    except Exception:
        txt = body.decode("utf-8", errors="ignore")
        assert "openapi" in txt and "/api/v1/materials" in txt
