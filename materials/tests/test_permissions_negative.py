from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_upload_for_course_forbidden_for_non_owner_teacher(client):
    # Teacher A owns the course; Teacher B attempts upload -> 403
    a = User.objects.create_user(username="ta", password="pw")
    b = User.objects.create_user(username="tb", password="pw")
    for u in (a, b):
        u.profile.role = "teacher"
        u.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=a, title="C1")
    assert client.login(username="tb", password="pw")
    r = client.post(f"/materials/course/{course.id}/upload/", data={"title": "X"})
    assert r.status_code == 403


@pytest.mark.django_db
def test_delete_material_forbidden_for_non_owner_teacher(client):
    # Teacher A owns the course/material; Teacher B attempts delete -> 403
    a = User.objects.create_user(username="ta2", password="pw")
    b = User.objects.create_user(username="tb2", password="pw")
    for u in (a, b):
        u.profile.role = "teacher"
        u.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=a, title="C2")
    m = Material.objects.create(course=course, uploaded_by=a, title="Doc", file="x.txt")
    assert client.login(username="tb2", password="pw")
    r = client.post(f"/materials/{m.id}/delete/")
    assert r.status_code == 403
