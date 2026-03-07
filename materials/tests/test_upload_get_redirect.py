from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.django_db
def test_upload_get_redirects_to_course_detail_for_owner(client):
    t = User.objects.create_user(username="tu1", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C")
    assert client.login(username="tu1", password="pw")
    r = client.get(f"/materials/course/{c.id}/upload/")
    assert r.status_code == 302
    assert f"/courses/{c.id}/" in r.headers.get("Location", "")
