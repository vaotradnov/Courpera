from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_material_delete_get_redirects_to_list_for_owner(client):
    t = User.objects.create_user(username="teach", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="T1")
    m = Material.objects.create(course=c, uploaded_by=t, title="Doc", file="x.txt")
    assert client.login(username="teach", password="pw")
    r = client.get(f"/materials/{m.id}/delete/")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/courses/")


@pytest.mark.django_db
def test_material_delete_post_redirects_to_course_detail(client):
    t = User.objects.create_user(username="teach2", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="T2")
    m = Material.objects.create(course=c, uploaded_by=t, title="Doc2", file="y.txt")
    assert client.login(username="teach2", password="pw")
    r = client.post(f"/materials/{m.id}/delete/")
    assert r.status_code == 302
    assert f"/courses/{c.id}/" in r.headers["Location"]
