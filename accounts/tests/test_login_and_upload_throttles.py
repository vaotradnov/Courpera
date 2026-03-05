from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from courses.models import Course


@pytest.mark.django_db
def test_login_per_session_throttle_messages_after_ten_attempts():
    # Create a user; attempt wrong password many times in one session
    User.objects.create_user(username="throt", password="correct")
    c = Client()
    for i in range(10):
        r = c.post("/accounts/login/", {"username": "throt", "password": "wrong"})
        assert r.status_code in (200, 302)
    # Next attempt should trigger throttle message (rendered form)
    r = c.post("/accounts/login/", {"username": "throt", "password": "wrong"})
    assert r.status_code == 200
    assert b"Too many login attempts" in r.content


@pytest.mark.django_db
def test_upload_per_session_throttle_enforced_at_five():
    # Teacher and course
    t = User.objects.create_user(username="tupload", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="U", description="")

    client = Client()
    assert client.login(username="tupload", password="pw")
    for i in range(5):
        f = SimpleUploadedFile(f"d{i}.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        r = client.post(f"/materials/course/{c.pk}/upload/", {"title": f"Doc{i}", "file": f})
        assert r.status_code in (302, 303)
    # Sixth should be throttled by message and redirect back to course detail
    f6 = SimpleUploadedFile("d6.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    r6 = client.post(
        f"/materials/course/{c.pk}/upload/", {"title": "Doc6", "file": f6}, follow=True
    )
    assert r6.status_code == 200
    assert b"Too many uploads" in r6.content
