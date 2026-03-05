from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from courses.models import Course
from materials.models import validate_upload


class Dummy:
    def __init__(self, name, size):
        self.name = name
        self.size = size


def test_validate_upload_size_and_type():
    # Invalid size
    big = Dummy("x.pdf", 25 * 1024 * 1024 + 1)
    with pytest.raises(Exception):
        validate_upload(big)
    # Invalid type
    small_bad = Dummy("x.exe", 1024)
    with pytest.raises(Exception):
        validate_upload(small_bad)
    # Valid
    ok = Dummy("x.pdf", 1024)
    validate_upload(ok)


@pytest.mark.django_db
def test_teacher_upload_view():
    t = User.objects.create_user(username="tup", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="C", description="")
    c = Client()
    assert c.login(username="tup", password="pw")
    f = SimpleUploadedFile("doc.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    r = c.post(f"/materials/course/{course.id}/upload/", {"title": "Doc", "file": f})
    assert r.status_code in (302, 303)
