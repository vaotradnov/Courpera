from __future__ import annotations

import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_profile_edit_and_password_change_pages_load(client):
    u = User.objects.create_user(username="u1", password="pw12345!A")
    client.force_login(u)
    r1 = client.get("/accounts/profile/")
    assert r1.status_code == 200
    r2 = client.get("/accounts/password/change/")
    assert r2.status_code == 200
