from __future__ import annotations

import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_teacher_search_supports_instructor_id_and_I_prefix(client):
    # Make a teacher to access search
    t = User.objects.create_user(username="teachx", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    # Create two users with profiles
    u1 = User.objects.create_user(username="alpha", email="alpha@example.com")
    u1.profile.student_number = "S0000123"
    u1.profile.save(update_fields=["student_number"])
    u2 = User.objects.create_user(username="beta", email="beta@example.com")
    u2.profile.instructor_id = "I777"
    u2.profile.save(update_fields=["instructor_id"])

    assert client.login(username="teachx", password="pw")

    # Search by instructor id should find u2
    r = client.get("/accounts/search/?q=I777")
    assert r.status_code == 200
    body = r.content.decode().lower()
    assert "beta" in body and "alpha" not in body

    # Search by I+user_id should match fallback
    r2 = client.get(f"/accounts/search/?q=I{u1.id}")
    assert r2.status_code == 200
    body2 = r2.content.decode().lower()
    assert "alpha" in body2
