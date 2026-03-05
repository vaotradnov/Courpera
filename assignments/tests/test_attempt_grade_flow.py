from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from assignments.models import Assignment, AssignmentType, Attempt, Grade
from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_paper_attempt_manual_grade_after_deadline_releases_and_records_grade(
    client, teacher_user, student_user
):
    c = Course.objects.create(owner=teacher_user, title="G")
    a = Assignment.objects.create(course=c, type=AssignmentType.PAPER, title="P", is_published=True)
    # Set deadline in the past to allow grading now
    a.deadline = timezone.now() - timezone.timedelta(days=1)
    a.save(update_fields=["deadline"])
    Enrolment.objects.create(course=c, student=student_user)
    att = Attempt.objects.create(assignment=a, student=student_user, attempt_no=1)

    client.force_login(teacher_user)
    url = reverse("assignments:attempt-grade", args=[att.id])
    r = client.post(url, data={"marks_awarded": 75, "feedback_text": "Good work"})
    assert r.status_code == 302
    att.refresh_from_db()
    assert att.released is True and att.marks_awarded == 75
    g = Grade.objects.filter(assignment=a, student=student_user).first()
    assert g and float(g.achieved_marks) == pytest.approx(75.0)


@pytest.mark.django_db
def test_quiz_attempt_override_requires_reason_when_changing_marks(
    client, teacher_user, student_user
):
    c = Course.objects.create(owner=teacher_user, title="Q")
    a = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="Q1", is_published=True, max_marks=100.0
    )
    Enrolment.objects.create(course=c, student=student_user)
    # Auto score 100 => auto marks 100
    att = Attempt.objects.create(assignment=a, student=student_user, attempt_no=1, score=100.0)

    client.force_login(teacher_user)
    url = reverse("assignments:attempt-grade", args=[att.id])
    # Change to 90 without override reason should be rejected
    r = client.post(url, data={"marks_awarded": 90})
    assert r.status_code == 302 and reverse("assignments:attempts", args=[a.pk]) in r.headers.get(
        "Location", ""
    )
    # Grade should not reflect the override
    g = Grade.objects.filter(assignment=a, student=student_user).first()
    assert g is None or float(g.achieved_marks) != pytest.approx(90.0)
