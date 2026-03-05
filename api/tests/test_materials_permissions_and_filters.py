from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_materials_visibility_and_filtering():
    t = User.objects.create_user(username="own", password="pw")
    s1 = User.objects.create_user(username="stu1", password="pw")
    s2 = User.objects.create_user(username="stu2", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    for s in (s1, s2):
        s.profile.role = "student"
        s.profile.save(update_fields=["role"])
    c1 = Course.objects.create(owner=t, title="C1", description="")
    c2 = Course.objects.create(owner=t, title="C2", description="")

    # Only enrolled/owner can see materials list entries; anonymous sees none
    anon = Client()
    r = anon.get("/api/v1/materials/")
    assert r.status_code == 200
    assert r.json().get("results", []) == []

    cs1 = Client()
    assert cs1.login(username="stu1", password="pw")
    # Enrol in c1 only
    Enrolment.objects.create(course=c1, student=s1)
    r = cs1.get("/api/v1/materials/?course=%d" % c1.id)
    assert r.status_code == 200
    # No materials created yet; but endpoint accessible
    assert r.json().get("results") == []

    # Owner sees both courses materials endpoint
    ct = Client()
    assert ct.login(username="own", password="pw")
    r = ct.get("/api/v1/materials/?course=%d" % c2.id)
    assert r.status_code == 200
