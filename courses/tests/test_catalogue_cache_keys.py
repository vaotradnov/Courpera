from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.django_db
def test_catalogue_cache_varies_by_query_params(client):
    # Create two courses with distinct titles
    t = User.objects.create_user(username="teach", password="pw")
    Course.objects.create(owner=t, title="Alpha Course")
    Course.objects.create(owner=t, title="Beta Course")

    r1 = client.get("/courses/?q=Alpha")
    r2 = client.get("/courses/?q=Beta")
    assert r1.status_code == 200 and r2.status_code == 200
    b1 = r1.content.decode()
    b2 = r2.content.decode()
    assert "Alpha Course" in b1 and "Beta Course" not in b1
    assert "Beta Course" in b2 and "Alpha Course" not in b2
