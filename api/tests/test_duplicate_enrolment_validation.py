from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_duplicate_enrolment_returns_400_not_500():
    # Teacher creates a course; student enrols twice via API
    t = User.objects.create_user(username="dup_t", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="dup_s", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Client()
    assert c.login(username="dup_t", password="pw")
    r = c.post(
        "/api/v1/courses/", {"title": "D", "description": ""}, content_type="application/json"
    )
    assert r.status_code in (200, 201)
    course_id = r.json()["id"]

    cs = Client()
    assert cs.login(username="dup_s", password="pw")
    r1 = cs.post("/api/v1/enrolments/", {"course": course_id}, content_type="application/json")
    assert r1.status_code in (200, 201)
    r2 = cs.post("/api/v1/enrolments/", {"course": course_id}, content_type="application/json")
    assert r2.status_code == 400
    assert "Already enrolled" in (r2.json().get("detail", "") or str(r2.content))
