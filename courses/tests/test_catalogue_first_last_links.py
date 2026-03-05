from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.django_db
def test_catalogue_shows_first_last_links_when_many_pages(client):
    t = User.objects.create_user(username="tcat", password="pw")
    try:
        p = t.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    # 28 courses -> 4 pages at 9/page
    for i in range(28):
        Course.objects.create(owner=t, title=f"C{i:02d}")
    # Visit page 2
    r = client.get("/courses/?page=2")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Page 2 of 4" in html
    assert "page=1" in html  # First
    assert "page=4" in html  # Last
