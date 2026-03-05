from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_non_owner_cannot_delete_material(client):
    owner = User.objects.create_user(username="own", password="pw")
    try:
        p = owner.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    other = User.objects.create_user(username="oth", password="pw")
    try:
        p = other.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    c = Course.objects.create(owner=owner, title="C")
    m = Material.objects.create(
        course=c,
        uploaded_by=owner,
        title="Doc",
        file=ContentFile(b"data", name="doc.pdf"),
        size_bytes=4,
        mime="application/pdf",
    )
    client.force_login(other)
    # Owner check occurs after fetching Material; view should raise PermissionDenied -> 403
    r = client.post(f"/materials/{m.id}/delete/")
    assert r.status_code in (403, 302)
    # Either blocked (403) or redirected by middleware to error page, but material must still exist
    assert Material.objects.filter(id=m.id).exists()
