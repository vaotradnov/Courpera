from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from courses.models import Course


@pytest.mark.django_db
def test_catalogue_filter_controls_present(client):
    url = reverse("courses:list")
    r = client.get(url)
    assert r.status_code == 200
    txt = r.text
    # Basic controls and labels
    assert 'name="subject"' in txt
    assert 'name="level"' in txt
    assert 'name="language"' in txt
    assert 'name="sort"' in txt
    assert "Results:" in txt


@pytest.mark.django_db
def test_course_detail_hero_and_subnav(client):
    teacher = User.objects.create_user(username="t3", password="pw")
    # Ensure profile role
    try:
        prof = teacher.profile
        prof.role = "teacher"
        prof.save(update_fields=["role"])
    except Exception:
        pass
    course = Course.objects.create(owner=teacher, title="My Course")
    client.force_login(teacher)
    url = reverse("courses:detail", kwargs={"pk": course.pk})
    r = client.get(url)
    assert r.status_code == 200
    txt = r.text
    # Title and subnav anchors
    assert course.title in txt
    assert '<nav class="subnav"' in txt
    assert "#syllabus" in txt and "#materials" in txt and "#assignments" in txt
