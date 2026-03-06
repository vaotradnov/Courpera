from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from assignments.models import Assignment, AssignmentType, Attempt
from assignments.services import update_attempts_allowed_if_safe
from courses.models import Course


@pytest.mark.django_db
def test_update_attempts_allowed_scenarios():
    t = User.objects.create_user(username="tt", password="pw")
    try:
        p = t.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    c = Course.objects.create(owner=t, title="T")
    a = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="Q1", attempts_allowed=2
    )

    # None/new_attempts invalid
    assert update_attempts_allowed_if_safe(a, None) is False
    assert update_attempts_allowed_if_safe(a, 0) is False

    # Equal to existing -> no-op
    assert update_attempts_allowed_if_safe(a, 2) is False

    # Lower than used -> no
    Attempt.objects.create(assignment=a, student=t, attempt_no=1)
    assert update_attempts_allowed_if_safe(a, 0) is False
    assert update_attempts_allowed_if_safe(a, 1) is True  # equals used, allowed
    a.refresh_from_db()
    assert a.attempts_allowed == 1

    # Increase allowed beyond used -> True
    assert update_attempts_allowed_if_safe(a, 3) is True
    a.refresh_from_db()
    assert a.attempts_allowed == 3


@pytest.mark.django_db
def test_update_attempts_uses_max_per_student_not_total():
    t = User.objects.create_user(username="tt2", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="T2")
    a = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="Q2", attempts_allowed=2
    )
    s1 = User.objects.create_user(username="s1a", password="pw")
    s2 = User.objects.create_user(username="s2a", password="pw")
    Attempt.objects.create(assignment=a, student=s1, attempt_no=1)
    Attempt.objects.create(assignment=a, student=s2, attempt_no=1)
    # Total attempts == 2, but per-student max == 1; lowering to 1 should be allowed
    assert update_attempts_allowed_if_safe(a, 1) is True
    a.refresh_from_db()
    assert a.attempts_allowed == 1
