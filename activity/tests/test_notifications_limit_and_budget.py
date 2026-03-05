from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from courses.models import Course, Enrolment
from materials.models import Material

try:
    from freezegun import freeze_time
except Exception:  # pragma: no cover - optional dependency fallback
    import contextlib

    @contextlib.contextmanager
    def freeze_time(*args, **kwargs):
        yield


@pytest.mark.django_db
def test_notifications_recent_limit_and_ordering():
    t = User.objects.create_user(username="nlim", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="nlim_s", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="Nlim", description="")
    with freeze_time("2025-01-01 00:00:00"):
        Enrolment.objects.create(course=c, student=s)  # notify teacher at T0
    # upload material to notify students at T1
    with freeze_time("2025-01-01 00:01:00"):
        f = SimpleUploadedFile("a.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        Material.objects.create(course=c, uploaded_by=t, title="Doc", file=f)

    ct = Client()
    assert ct.login(username="nlim", password="pw")
    r = ct.get("/activity/notifications/recent/?limit=1")
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("results", [])) == 1
    # Newest-first ordering is expected
    r_all = ct.get("/activity/notifications/recent/?limit=10")
    items = r_all.json().get("results", [])
    created = [i.get("created_at") for i in items]
    assert created == sorted(created, reverse=True)


@pytest.mark.django_db
@pytest.mark.performance
def test_notifications_recent_query_budget():
    t = User.objects.create_user(username="nbud", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="nbud_s", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="Nbud", description="")
    Enrolment.objects.create(course=c, student=s)
    ct = Client()
    assert ct.login(username="nbud", password="pw")
    with CaptureQueriesContext(connection) as ctx:
        r = ct.get("/activity/notifications/recent/?limit=5")
        assert r.status_code == 200
    assert len(ctx.captured_queries) <= 5


@pytest.mark.django_db
def test_notifications_limit_invalid_param_falls_back_to_default():
    t = User.objects.create_user(username="ninv", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="ninv_s", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="Ninv", description="")
    Enrolment.objects.create(course=c, student=s)
    ct = Client()
    assert ct.login(username="ninv", password="pw")
    # invalid limit should not 500; should return 200 and default number of items (<=10)
    r = ct.get("/activity/notifications/recent/?limit=abc")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("results", []), list)
    assert len(data.get("results", [])) <= 10
