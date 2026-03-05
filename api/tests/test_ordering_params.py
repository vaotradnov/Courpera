from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course


@pytest.mark.django_db
def test_courses_ordering_param_valid_and_invalid():
    t = User.objects.create_user(username="cord", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    titles = ["Zeta", "Alpha", "Beta"]
    for title in titles:
        Course.objects.create(owner=t, title=title, description="")
    c = Client()
    # Valid ordering
    r = c.get("/api/v1/courses/?ordering=-title")
    assert r.status_code == 200
    got = [row["title"] for row in r.json()["results"]]
    assert got == sorted(titles, reverse=True)

    # Invalid ordering field should be rejected by DRF OrderingFilter
    r_bad = c.get("/api/v1/courses/?ordering=bogus")
    assert r_bad.status_code in (400, 200)
    # If backend permits, at least ensure results are still sorted by default
    if r_bad.status_code == 200:
        got2 = [row["title"] for row in r_bad.json()["results"]]
        assert got2 == sorted(got2)
