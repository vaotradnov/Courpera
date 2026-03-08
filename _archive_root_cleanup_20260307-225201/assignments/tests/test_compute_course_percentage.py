from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from assignments.models import Assignment, AssignmentType, Grade
from assignments.utils import compute_course_percentage
from courses.models import Course


@pytest.mark.django_db
def test_compute_course_percentage_published_and_released_filters():
    t = User.objects.create_user(username="teacher", password="pw")
    s = User.objects.create_user(username="stud", password="pw")
    c = Course.objects.create(owner=t, title="Course")
    a_pub = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="Pub", is_published=True, max_marks=100
    )
    a_unpub = Assignment.objects.create(
        course=c, type=AssignmentType.PAPER, title="Unpub", is_published=False, max_marks=50
    )

    # Published grade (released)
    Grade.objects.create(
        assignment=a_pub,
        course=c,
        student=s,
        achieved_marks=60,
        max_marks=100,
        released_at="2026-03-05T00:00:00Z",
    )
    # Unpublished grade should not count
    Grade.objects.create(assignment=a_unpub, course=c, student=s, achieved_marks=50, max_marks=50)

    pct_all = compute_course_percentage(c, s, only_released=False)
    assert pct_all == 60.0
    pct_released = compute_course_percentage(c, s, only_released=True)
    assert pct_released == 60.0


@pytest.mark.django_db
def test_compute_course_percentage_handles_zero_and_empty():
    t = User.objects.create_user(username="teacher2", password="pw")
    s = User.objects.create_user(username="stud2", password="pw")
    c = Course.objects.create(owner=t, title="Course2")

    # No grades -> 0.0
    assert compute_course_percentage(c, s) == 0.0

    # Zero max marks edge-case -> 0.0 (avoid division by zero)
    a = Assignment.objects.create(
        course=c, type=AssignmentType.EXAM, title="E", is_published=True, max_marks=0
    )
    Grade.objects.create(assignment=a, course=c, student=s, achieved_marks=0, max_marks=0)
    assert compute_course_percentage(c, s) == 0.0
