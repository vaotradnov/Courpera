from __future__ import annotations

import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_enrolments_list_shape_for_student(client):
    s = User.objects.create_user(username="stud", password="pw")
    try:
        p = s.profile
        p.role = "student"
        p.save(update_fields=["role"])
    except Exception:
        pass
    client.force_login(s)
    r = client.get("/api/v1/enrolments/")
    assert r.status_code == 200
    data = r.json()
    # Paginated shape
    assert isinstance(data, dict)
    assert "count" in data and "results" in data
    assert isinstance(data["results"], list)
