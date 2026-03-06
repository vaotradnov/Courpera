from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from assignments.models import Assignment, AssignmentType, Grade
from courses.gradebook import build_grade_rows, gradebook_csv_response
from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_build_grade_rows_and_csv_formatting():
    t = User.objects.create_user(username="tgb", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C1")
    a1 = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="A1", is_published=True
    )
    a2 = Assignment.objects.create(
        course=c, type=AssignmentType.EXAM, title="A2", is_published=True
    )

    s1 = User.objects.create_user(username="s1", password="pw")
    s1.profile.role = "student"
    s1.profile.save(update_fields=["role"])
    s2 = User.objects.create_user(username="s2", password="pw")
    s2.profile.role = "student"
    s2.profile.save(update_fields=["role"])
    Enrolment.objects.create(course=c, student=s1)
    Enrolment.objects.create(course=c, student=s2)

    # Create grades: one with integer marks, one with float
    Grade.objects.create(assignment=a1, course=c, student=s1, achieved_marks=80.0, max_marks=100.0)
    Grade.objects.create(assignment=a2, course=c, student=s1, achieved_marks=7.5, max_marks=10.0)

    rows = build_grade_rows(c, [a1, a2])
    assert s1.id in rows and a1.id in rows[s1.id]

    # CSV response should format 80.0 as 80 and 7.5 as 7.5
    resp = gradebook_csv_response(c)
    body = resp.content.decode()
    assert "username,S-ID,A1,A2,course %" in body.splitlines()[0]
    # Find the row for s1
    lines = [ln for ln in body.splitlines() if ln.startswith("s1,")]
    assert lines
    row = lines[0]
    assert "80/100" in row and "7.5/10" in row
