from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_materials_serializer_includes_expected_fields():
    t = User.objects.create_user(username="smat", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="S", description="")
    f = SimpleUploadedFile("a.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    m = Material.objects.create(course=c, uploaded_by=t, title="A", file=f)

    client = Client()
    assert client.login(username="smat", password="pw")
    r = client.get(f"/api/v1/materials/?course={c.id}")
    assert r.status_code == 200
    data = r.json()
    row = data["results"][0]
    assert {"id", "course", "title", "size_bytes", "mime", "created_at", "file_url"} <= set(
        row.keys()
    )
    # Ensure pagination metadata keys exist (values may be null)
    assert {"count", "next", "previous"} <= set(data.keys())


@pytest.mark.django_db
def test_course_detail_forbidden_when_not_owner_or_enrolled():
    t = User.objects.create_user(username="ownr", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Client()
    assert c.login(username="ownr", password="pw")
    # Create a course via API to get id easily
    r_create = c.post(
        "/api/v1/courses/", {"title": "X", "description": ""}, content_type="application/json"
    )
    assert r_create.status_code in (200, 201)
    course_id = r_create.json().get("id") or 1

    # Anonymous forbidden
    anon = Client()
    r = anon.get(f"/api/v1/courses/{course_id}/")
    assert r.status_code == 403

    # Different logged-in user also forbidden
    u2 = User.objects.create_user(username="other", password="pw")
    c2 = Client()
    assert c2.login(username="other", password="pw")
    r2 = c2.get(f"/api/v1/courses/{course_id}/")
    assert r2.status_code == 403


@pytest.mark.django_db
def test_courses_pagination_metadata_present():
    t = User.objects.create_user(username="pmeta", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    for i in range(30):
        Course.objects.create(owner=t, title=f"PX{i}", description="")
    c = Client()
    r = c.get("/api/v1/courses/")
    data = r.json()
    assert set(["count", "next", "previous", "results"]) <= set(data.keys())


@pytest.mark.django_db
def test_course_detail_query_budget_owner():
    t = User.objects.create_user(username="qdet", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="QDet", description="")
    c = Client()
    assert c.login(username="qdet", password="pw")
    with CaptureQueriesContext(connection) as ctx:
        r = c.get(f"/api/v1/courses/{course.id}/")
        assert r.status_code == 200
    assert len(ctx.captured_queries) <= 5
