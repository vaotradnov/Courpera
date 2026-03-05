from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_upload_throttle_blocks_sixth_within_minute(client):
    t = User.objects.create_user(username="mt", password="pw")
    try:
        p = t.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    c = Course.objects.create(owner=t, title="M")
    client.force_login(t)
    url = f"/materials/course/{c.id}/upload/"

    def upload_one(i):
        f = SimpleUploadedFile(f"f{i}.pdf", b"%PDF-1.4\n%...", content_type="application/pdf")
        return client.post(url, data={"title": f"Doc{i}", "file": f})

    for i in range(5):
        r = upload_one(i)
        assert r.status_code == 302
    # Sixth should be throttled and not increase count
    before = Material.objects.filter(course=c).count()
    r6 = upload_one(6)
    assert r6.status_code == 302
    after = Material.objects.filter(course=c).count()
    assert after == before


@pytest.mark.django_db
def test_bad_extension_is_rejected(client):
    t = User.objects.create_user(username="mt2", password="pw")
    try:
        p = t.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    c = Course.objects.create(owner=t, title="M2")
    client.force_login(t)
    url = f"/materials/course/{c.id}/upload/"
    bad = SimpleUploadedFile("sneaky.exe", b"fake", content_type="application/octet-stream")
    r = client.post(url, data={"title": "Sneaky", "file": bad})
    assert r.status_code == 302
    assert Material.objects.filter(course=c).count() == 0
