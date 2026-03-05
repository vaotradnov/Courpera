from __future__ import annotations

from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment


def _pos(haystack: str, needle: str) -> int:
    i = haystack.find(needle)
    assert i >= 0, f"'{needle}' not found in response"
    return i


def test_sort_by_most_enrolled_orders_desc(db):
    t = User.objects.create_user(username="teach_sort", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s1 = User.objects.create_user(username="s1_sort", password="pw")
    s1.profile.role = "student"
    s1.profile.save(update_fields=["role"])
    s2 = User.objects.create_user(username="s2_sort", password="pw")
    s2.profile.role = "student"
    s2.profile.save(update_fields=["role"])

    cA = Course.objects.create(owner=t, title="AAA", description="")
    cB = Course.objects.create(owner=t, title="BBB", description="")
    cC = Course.objects.create(owner=t, title="CCC", description="")

    Enrolment.objects.create(course=cA, student=s1)
    Enrolment.objects.create(course=cA, student=s2)
    Enrolment.objects.create(course=cB, student=s1)
    # cC has zero enrolments

    client = Client()
    resp = client.get("/courses/?sort=enrolled")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="ignore")
    # Expect AAA first (2), then BBB (1), then CCC (0)
    posA, posB, posC = _pos(body, "AAA"), _pos(body, "BBB"), _pos(body, "CCC")
    assert posA < posB < posC


def test_filters_subject_level_language(db):
    t = User.objects.create_user(username="teach_f", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    Course.objects.create(
        owner=t, title="AI 101", description="", subject="AI", level="advanced", language="Spanish"
    )
    Course.objects.create(
        owner=t,
        title="Math 101",
        description="",
        subject="Math",
        level="beginner",
        language="English",
    )

    client = Client()
    # Filter subject AI
    r1 = client.get("/courses/?subject=AI")
    assert r1.status_code == 200
    body1 = r1.content.decode("utf-8", errors="ignore")
    assert "AI 101" in body1 and "Math 101" not in body1
    # Filter level beginner
    r2 = client.get("/courses/?level=beginner")
    body2 = r2.content.decode("utf-8", errors="ignore")
    assert "Math 101" in body2 and "AI 101" not in body2
    # Filter language Spanish
    r3 = client.get("/courses/?language=Spanish")
    body3 = r3.content.decode("utf-8", errors="ignore")
    assert "AI 101" in body3 and "Math 101" not in body3
