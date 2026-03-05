from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course


@pytest.mark.django_db
def test_courses_ordering_by_title_across_pages_and_out_of_range():
    t = User.objects.create_user(username="porder", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    titles = [f"Course {i:03d}" for i in range(1, 41)]
    for title in titles:
        Course.objects.create(owner=t, title=title, description="")

    c = Client()
    # First page
    r1 = c.get("/api/v1/courses/?page_size=15&page=1")
    assert r1.status_code == 200
    res1 = [row["title"] for row in r1.json()["results"]]
    assert res1 == sorted(res1)
    # Second page continues ordering
    r2 = c.get("/api/v1/courses/?page_size=15&page=2")
    assert r2.status_code == 200
    res2 = [row["title"] for row in r2.json()["results"]]
    assert res2 == sorted(res2)
    # Combined results in order
    combined = res1 + res2
    assert combined == sorted(combined)

    # Out-of-range page returns empty results (or last page depending on paginator),
    # ensure consistent count and results list type
    r_out = c.get("/api/v1/courses/?page=999")
    assert r_out.status_code in (200, 404)
    if r_out.status_code == 200:
        payload = r_out.json()
        assert isinstance(payload.get("results", []), list)
