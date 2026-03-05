from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_gradebook_html_view_smoke(client, make_course, teacher_user):
    c = make_course(owner=teacher_user, title="GB")
    client.force_login(teacher_user)
    url = reverse("courses:gradebook", args=[c.pk])
    r = client.get(url)
    assert r.status_code == 200
    assert "Gradebook" in r.content.decode() or "Students" in r.content.decode()
