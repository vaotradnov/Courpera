from __future__ import annotations

import io

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_owner_can_delete_material(client):
    teacher = User.objects.create_user(username="teach", password="pw")
    # mark as teacher role if profiles exist
    try:
        p = teacher.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    course = Course.objects.create(owner=teacher, title="C1")
    # Create a small fake file
    mat = Material.objects.create(
        course=course,
        uploaded_by=teacher,
        title="doc",
        file=ContentFile(b"hello", name="doc.pdf"),
        size_bytes=5,
        mime="application/pdf",
    )
    client.force_login(teacher)
    r = client.post(f"/materials/{mat.id}/delete/")
    assert r.status_code == 302
    assert not Material.objects.filter(id=mat.id).exists()
