from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
@pytest.mark.security
def test_post_without_csrf_is_rejected_on_html_view():
    u = User.objects.create_user(username="csrfu", password="pw")
    c = Client(enforce_csrf_checks=True)
    assert c.login(username="csrfu", password="pw")
    # POST without csrf_token in body should be 403
    r = c.post("/activity/notifications/mark-all-read/")
    assert r.status_code == 403


@pytest.mark.django_db
@pytest.mark.security
def test_student_and_anon_cannot_access_teacher_search_html():
    # student cannot access
    s = User.objects.create_user(username="std", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    cs = Client()
    assert cs.login(username="std", password="pw")
    r = cs.get("/accounts/search/?q=x")
    assert r.status_code == 403
    # anon also forbidden
    anon = Client()
    r2 = anon.get("/accounts/search/?q=x")
    assert r2.status_code in (302, 403)  # may redirect to login or show 403
