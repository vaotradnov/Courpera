from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from courses.models import Course


@pytest.mark.django_db
def test_course_detail_accordion_aria_defaults(client):
    t = User.objects.create_user(username="tacc", password="pw")
    try:
        p = t.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    c = Course.objects.create(owner=t, title="A11y Course")
    client.force_login(t)
    r = client.get(f"/courses/{c.id}/")
    assert r.status_code == 200
    html = r.content.decode()
    assert 'aria-expanded="true"' in html
    assert 'aria-expanded="false"' in html
    assert 'id="outcomes-panel"' in html and 'class="accordion-panel"' in html
    # The second panel should be hidden initially
    assert 'id="outcomes-panel" class="accordion-panel" hidden' in html
