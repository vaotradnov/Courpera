from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize(
    "page_size, expected_max",
    [
        ("-5", 20),  # fallback to default page size
        ("abc", 20),  # non-int -> default
        ("9999", 100),  # capped at max_page_size
    ],
)
def test_courses_page_size_matrix(client, page_size, expected_max):
    owner = User.objects.create_user(username="o_pg", password="pw")
    # Ensure enough records
    for i in range(120):
        Course.objects.create(owner=owner, title=f"C{i:03d}")
    r = client.get(f"/api/v1/courses/?page_size={page_size}")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict) and isinstance(data.get("results"), list)
    assert len(data["results"]) <= expected_max
