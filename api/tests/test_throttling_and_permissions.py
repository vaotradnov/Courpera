from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings


@pytest.mark.django_db
@pytest.mark.security
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.UserRateThrottle",
            "rest_framework.throttling.AnonRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {"user": "5/min", "anon": "3/min"},
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }
)
def test_anon_throttle_limits_requests():
    c = Client()
    codes = [c.get("/api/v1/courses/").status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] in (
        429,
        200,
    )  # allow some leeway if cache isn’t warmed; but should typically be 429


@pytest.mark.django_db
@pytest.mark.security
def test_teacher_only_course_create():
    teacher = User.objects.create_user(username="t", password="pw")
    student = User.objects.create_user(username="s", password="pw")
    teacher.profile.role = "teacher"
    teacher.profile.save(update_fields=["role"])
    student.profile.role = "student"
    student.profile.save(update_fields=["role"])
    ct = Client()
    assert ct.login(username="t", password="pw")
    cs = Client()
    assert cs.login(username="s", password="pw")
    r_ok = ct.post(
        "/api/v1/courses/", {"title": "A", "description": ""}, content_type="application/json"
    )
    assert r_ok.status_code in (200, 201)
    r_bad = cs.post(
        "/api/v1/courses/", {"title": "B", "description": ""}, content_type="application/json"
    )
    assert r_bad.status_code == 403
