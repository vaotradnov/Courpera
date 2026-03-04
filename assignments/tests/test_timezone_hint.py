from __future__ import annotations

from django.test import Client
from django.contrib.auth.models import User

from courses.models import Course


def test_assignment_create_shows_timezone_hint(db):
    t = User.objects.create_user(username="teach_tz", password="pw")
    t.profile.role = "teacher"; t.profile.timezone = "UTC"; t.profile.save(update_fields=["role", "timezone"])
    c = Course.objects.create(owner=t, title="TZ", description="")
    client = Client(); assert client.login(username="teach_tz", password="pw")
    resp = client.get(f"/assignments/course/{c.id}/create/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="ignore")
    assert "Times shown in your timezone: UTC" in body

