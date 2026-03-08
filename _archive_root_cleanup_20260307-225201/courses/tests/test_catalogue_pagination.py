from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from courses.models import Course


@pytest.mark.django_db
def test_catalogue_paginates_and_links(client):
    teacher = User.objects.create_user(username="t1", password="pw")
    # Make teacher an owner by creating profile role via signal default; set role manually if needed
    try:
        prof = teacher.profile
        prof.role = "teacher"
        prof.save(update_fields=["role"])
    except Exception:
        pass

    # Create 15 courses to exceed page size (9)
    items = []
    for i in range(15):
        items.append(Course.objects.create(owner=teacher, title=f"Course {i:02d}", description="d"))

    url = reverse("courses:list")
    r1 = client.get(url)
    assert r1.status_code == 200
    # Count cards on page 1
    count_cards = len(re.findall(r"<article class=\"card\">", r1.content.decode()))
    assert count_cards == 9
    assert "Page 1 of 2" in r1.text
    assert "?page=2" in r1.text

    r2 = client.get(url + "?page=2")
    assert r2.status_code == 200
    count_cards_2 = len(re.findall(r"<article class=\"card\">", r2.content.decode()))
    assert count_cards_2 == 6
    assert "Page 2 of 2" in r2.text


@pytest.mark.django_db
def test_catalogue_cache_headers_and_vary_cookie(client):
    teacher = User.objects.create_user(username="t2", password="pw")
    Course.objects.create(owner=teacher, title="Alpha", description="d")
    url = reverse("courses:list")
    r = client.get(url)
    assert r.status_code == 200
    # cache_page decorator should attach a Cache-Control max-age header
    cc = r.headers.get("Cache-Control", "")
    assert "max-age" in cc.lower()
    vary = r.headers.get("Vary", "")
    # Vary on Cookie to isolate per-user badges state
    assert "cookie" in vary.lower()
