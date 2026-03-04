from __future__ import annotations

from django.test import Client
from django.contrib.auth.models import User

from courses.models import Course


def test_teacher_can_create_with_meta_fields(db):
    t = User.objects.create_user(username="teach_meta_c", password="pw")
    t.profile.role = "teacher"; t.profile.save(update_fields=["role"])
    c = Client(); assert c.login(username="teach_meta_c", password="pw")
    resp = c.post("/courses/create/", {
        "title": "MetaCourse",
        "description": "Desc",
        "subject": "Data",
        "level": "intermediate",
        "language": "French",
    }, follow=True)
    assert resp.status_code == 200
    course = Course.objects.get(title="MetaCourse")
    assert course.subject == "Data"
    assert course.level == "intermediate"
    assert course.language == "French"


def test_teacher_can_edit_meta_fields(db):
    t = User.objects.create_user(username="teach_meta_e", password="pw")
    t.profile.role = "teacher"; t.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="EditMe", description="", subject="AI", level="beginner", language="English")
    c = Client(); assert c.login(username="teach_meta_e", password="pw")
    r = c.post(f"/courses/{course.id}/edit/", {
        "title": "EditMe",
        "description": "Changed",
        "subject": "Math",
        "level": "advanced",
        "language": "Spanish",
    }, follow=True)
    assert r.status_code == 200
    course.refresh_from_db()
    assert course.subject == "Math"
    assert course.level == "advanced"
    assert course.language == "Spanish"

