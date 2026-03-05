from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_feedback_requires_enrolment_and_allows_update_by_owner():
    t = User.objects.create_user(username="tfeed", password="pw")
    s = User.objects.create_user(username="sfeed", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="CF", description="")

    client = Client()
    assert client.login(username="sfeed", password="pw")
    # Cannot create feedback when not enrolled
    r = client.post(
        "/api/v1/feedback/",
        {
            "course": c.id,
            "rating": 5,
            "comment": "Great",
            "anonymous": False,
        },
        content_type="application/json",
    )
    assert r.status_code == 403

    # Enrol then create
    Enrolment.objects.create(course=c, student=s)
    r = client.post(
        "/api/v1/feedback/",
        {
            "course": c.id,
            "rating": 4,
            "comment": "Good",
            "anonymous": True,
        },
        content_type="application/json",
    )
    assert r.status_code in (200, 201)
    fb_id = r.json().get("id")
    # Update own feedback
    r2 = client.patch(f"/api/v1/feedback/{fb_id}/", {"rating": 3}, content_type="application/json")
    assert r2.status_code in (200, 202)

    # Another user cannot update student's feedback
    s2 = User.objects.create_user(username="sfeed2", password="pw")
    s2.profile.role = "student"
    s2.profile.save(update_fields=["role"])
    client.logout()
    assert client.login(username="sfeed2", password="pw")
    r3 = client.patch(f"/api/v1/feedback/{fb_id}/", {"rating": 1}, content_type="application/json")
    assert r3.status_code == 403
