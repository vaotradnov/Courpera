from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.django_db
def test_sort_fallback_to_title_when_invalid(client):
    owner = User.objects.create_user(username="own", password="pw")
    Course.objects.create(owner=owner, title="A")
    Course.objects.create(owner=owner, title="B")
    r = client.get("/courses/?sort=not-a-valid-field")
    assert r.status_code == 200
    html = r.content.decode()
    # 'A' appears before 'B'
    assert html.index("A") < html.index("B")


@pytest.mark.django_db
def test_empty_state_shows_message(client):
    # Ensure DB empty for courses
    from courses.models import Course

    Course.objects.all().delete()
    r = client.get("/courses/?subject=__no_such__")
    assert r.status_code == 200
    assert "No courses yet." in r.content.decode()
