from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_student_cannot_create_course_via_api():
    student = User.objects.create_user(username="stu_api", password="pw")
    # default role is student via profile signal
    c = Client()
    assert c.login(username="stu_api", password="pw")
    r = c.post(
        "/api/v1/courses/",
        {"title": "NotAllowed", "description": ""},
        content_type="application/json",
    )
    assert r.status_code == 403
