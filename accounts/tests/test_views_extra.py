from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_home_redirects_by_role(client):
    u = User.objects.create_user(username="stu", password="pw")
    u.profile.role = "student"
    u.profile.save(update_fields=["role"])
    assert client.login(username="stu", password="pw")
    r = client.get(reverse("accounts:home"))
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/accounts/home/student/") or r.headers[
        "Location"
    ].endswith("/accounts/home-student/")

    t = User.objects.create_user(username="teach", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    assert client.login(username="teach", password="pw")
    r2 = client.get(reverse("accounts:home"))
    assert r2.status_code == 302
    assert r2.headers["Location"].endswith("/accounts/home/teacher/") or r2.headers[
        "Location"
    ].endswith("/accounts/home-teacher/")


@pytest.mark.django_db
def test_logout_allows_get(client):
    u = User.objects.create_user(username="u", password="pw")
    assert client.login(username="u", password="pw")
    r = client.get(reverse("accounts:logout"))
    assert r.status_code in (200, 302)


@pytest.mark.django_db
def test_password_forgot_mismatch_and_throttle(client, settings):
    u = User.objects.create_user(username="u2", email="u2@example.com", password="pw")
    url = reverse("accounts:password-forgot")
    # Mismatch passwords
    r = client.post(
        url,
        data={
            "identifier": "u2",
            "secret_word": "wrong",
            "new_password1": "Passw0rd!Passw0rd!",
            "new_password2": "Mismatch123!",
        },
    )
    assert r.status_code == 200
    body = r.content.decode().lower()
    assert "passwords do not match" in body
    # Hit throttle quickly
    for _ in range(5):
        client.post(
            url,
            data={
                "identifier": "u2",
                "secret_word": "wrong",
                "new_password1": "Passw0rd!Passw0rd!",
                "new_password2": "Passw0rd!Passw0rd!",
            },
        )
    r2 = client.post(
        url,
        data={
            "identifier": "u2",
            "secret_word": "wrong",
            "new_password1": "Passw0rd!Passw0rd!",
            "new_password2": "Passw0rd!Passw0rd!",
        },
    )
    assert r2.status_code == 200
    assert "too many reset attempts" in r2.content.decode().lower()


@pytest.mark.django_db
def test_login_open_redirect_guard(client, settings):
    # Ensure next to external host is ignored
    u = User.objects.create_user(username="u3", password="Strong#Passw0rd")
    url = reverse("accounts:login") + "?next=http://evil.com/"
    r = client.post(url, data={"username": "u3", "password": "Strong#Passw0rd"})
    assert r.status_code in (302, 303)
    # Should not redirect to external domain
    loc = r.headers.get("Location", "")
    assert loc.startswith("/") and "evil.com" not in loc


@pytest.mark.django_db
def test_avatar_proxy_bad_size_returns_400(client):
    # 8px is below 16 minimum, should 400
    r = client.get("/accounts/avatar/1/8/")
    assert r.status_code == 400
    # 300px is above 256 maximum, should 400
    r2 = client.get("/accounts/avatar/1/300/")
    assert r2.status_code == 400
