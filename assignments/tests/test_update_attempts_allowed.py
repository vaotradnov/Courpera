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
