from __future__ import annotations

import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_student_cannot_access_course_create_page(client):
    s = User.objects.create_user(username="stu", password="pw")
    # default role is student via signal
    assert client.login(username="stu", password="pw")
    r_get = client.get("/courses/create/")
    assert r_get.status_code == 403
    r_post = client.post(
        "/courses/create/",
        {"title": "X", "description": ""},
    )
    assert r_post.status_code == 403


@pytest.mark.django_db
def test_teacher_can_access_course_create_page(client):
    t = User.objects.create_user(username="teach_x", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    assert client.login(username="teach_x", password="pw")
    r_get = client.get("/courses/create/")
    assert r_get.status_code == 200


@pytest.mark.django_db
def test_student_catalogue_hides_create_button(client):
    s = User.objects.create_user(username="stu2", password="pw")
    assert client.login(username="stu2", password="pw")
    r = client.get("/courses/")
    assert r.status_code == 200
    # Ensure the Create button isn’t present for students
    assert "/courses/create/" not in r.text
