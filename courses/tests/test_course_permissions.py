from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_course_visibility_owner_enrolled_limited():
    teacher = User.objects.create_user(username="t1", password="pw")
    student = User.objects.create_user(username="s1", password="pw")
    teacher.profile.role = "teacher"
    teacher.profile.save(update_fields=["role"])
    student.profile.role = "student"
    student.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=teacher, title="T", description="D")

    c = Client()
    # Non-enrolled student: limited view (200 but no materials UI)
    assert c.login(username="s1", password="pw")
    r = c.get(f"/courses/{course.id}/")
    assert r.status_code == 200
    assert b"Course chat" not in r.content  # guarded by owner/enrolled
    c.logout()

    # Owner: full view
    assert c.login(username="t1", password="pw")
    r = c.get(f"/courses/{course.id}/")
    assert r.status_code == 200
    assert b"Course chat" in r.content
    c.logout()

    # Enrolled student: full view
    Enrolment.objects.create(course=course, student=student)
    assert c.login(username="s1", password="pw")
    r = c.get(f"/courses/{course.id}/")
    assert r.status_code == 200
    assert b"Course chat" in r.content
