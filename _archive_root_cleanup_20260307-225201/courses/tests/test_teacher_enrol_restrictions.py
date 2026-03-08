from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from courses.models import Course


@pytest.mark.django_db
def test_teacher_does_not_see_enrol_actions_on_catalogue(client):
    # Two teachers; t2 owns the course, t1 is browsing
    t1 = User.objects.create_user(username="t1", password="pw")
    t1.profile.role = "teacher"
    t1.profile.save(update_fields=["role"])

    t2 = User.objects.create_user(username="t2", password="pw")
    t2.profile.role = "teacher"
    t2.profile.save(update_fields=["role"])

    c = Course.objects.create(owner=t2, title="Alpha", description="d")

    assert client.login(username="t1", password="pw")
    r = client.get(reverse("courses:list"))
    assert r.status_code == 200
    # No enrol/unenrol buttons for teachers
    body = r.text
    assert f"/courses/{c.id}/enrol/" not in body
    assert f"/courses/{c.id}/unenrol/" not in body


@pytest.mark.django_db
def test_teacher_does_not_see_enrol_on_detail_and_cannot_enrol_post(client):
    t = User.objects.create_user(username="t", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])

    owner = User.objects.create_user(username="owner", password="pw")
    owner.profile.role = "teacher"
    owner.profile.save(update_fields=["role"])

    c = Course.objects.create(owner=owner, title="Beta", description="d")

    assert client.login(username="t", password="pw")
    # Detail page should not show enrol CTA for teacher
    r = client.get(reverse("courses:detail", args=[c.id]))
    assert r.status_code in (200, 403)  # detail may be 403 for non-enrolled
    if r.status_code == 200:
        assert "Enrol for free" not in r.text

    # Direct POST to enrol endpoint must be forbidden for teachers
    r2 = client.post(reverse("courses:enrol", args=[c.id]))
    assert r2.status_code == 403
