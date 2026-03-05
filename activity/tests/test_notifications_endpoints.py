from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment
from materials.models import Material


@pytest.mark.django_db
def test_notifications_recent_and_mark_all_read():
    # Teacher and student
    t = User.objects.create_user(username="tnote", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="snote", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="N", description="")

    # Student enrolment -> notify teacher
    Enrolment.objects.create(course=c, student=s)

    # Teacher recent JSON shows unread >= 1
    ct = Client()
    assert ct.login(username="tnote", password="pw")
    r = ct.get("/activity/notifications/recent/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["unread"] >= 1
    assert len(payload["results"]) >= 1

    # Mark all read
    r2 = ct.post("/activity/notifications/mark-all-read/")
    assert r2.status_code in (302, 303)
    r3 = ct.get("/activity/notifications/recent/")
    assert r3.json()["unread"] == 0


@pytest.mark.django_db
def test_student_receives_material_notification_in_recent_json():
    t = User.objects.create_user(username="tnote2", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="snote2", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="N2", description="")
    Enrolment.objects.create(course=c, student=s)

    # Upload material -> notify enrolled students
    Material.objects.create(course=c, uploaded_by=t, title="Slides", file="slides.pdf")

    cs = Client()
    assert cs.login(username="snote2", password="pw")
    r = cs.get("/activity/notifications/recent/")
    assert r.status_code == 200
    data = r.json()
    assert data["unread"] >= 1
    assert any("Slides" in (item.get("message") or "") for item in data.get("results", []))
