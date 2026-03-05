from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_profile_update_success_and_wrong_password_error(client):
    u = User.objects.create_user(username="profu", password="pw", email="old@example.com")
    u.profile.role = "student"
    u.profile.save(update_fields=["role"])
    assert client.login(username="profu", password="pw")
    url = reverse("accounts:profile")
    # Wrong password -> error stays on page (status 200)
    r1 = client.post(
        url,
        data={
            "full_name": "Name",
            "timezone": "UTC",
            "email": "new@example.com",
            "current_password": "wrong",
        },
    )
    assert r1.status_code == 200
    assert "incorrect" in r1.content.decode().lower()
    # Correct password -> redirect and email updated
    r2 = client.post(
        url,
        data={
            "full_name": "Name",
            "timezone": "UTC",
            "email": "new@example.com",
            "current_password": "pw",
        },
    )
    assert r2.status_code == 302
    u.refresh_from_db()
    assert u.email == "new@example.com"


@pytest.mark.django_db
def test_registration_duplicate_email_and_password_mismatch(client):
    User.objects.create_user(username="other", password="pw", email="dup@example.com")
    url = reverse("accounts:register")
    # Duplicate email
    r1 = client.post(
        url,
        data={
            "username": "newu",
            "email": "dup@example.com",
            "role": "student",
            "secret_word": "secret123",
            "password1": "Passw0rd!Passw0rd!",
            "password2": "Passw0rd!Passw0rd!",
        },
    )
    assert r1.status_code == 200
    assert "already exists" in r1.content.decode()
    # Password mismatch
    r2 = client.post(
        url,
        data={
            "username": "newu2",
            "email": "unique@example.com",
            "role": "student",
            "secret_word": "secret123",
            "password1": "Passw0rd!Passw0rd!",
            "password2": "Mismatch123!",
        },
    )
    assert r2.status_code == 200
    assert "password" in r2.content.decode().lower()


@pytest.mark.django_db
def test_password_change_done_smoke(client):
    u = User.objects.create_user(username="pcu", password="pw")
    assert client.login(username="pcu", password="pw")
    r = client.get(reverse("accounts:password-change-done"))
    assert r.status_code == 200
