from __future__ import annotations

import pytest
from django.urls import reverse

from assignments.models import Assignment, AssignmentType, Attempt, Grade
from courses.models import Enrolment


@pytest.mark.django_db
def test_manage_update_meta_policy_change_triggers_recalc(client, teacher_user, student_user):
    # Create course and paper assignment with two attempts (40 and 60 marks)
    t = teacher_user
    s = student_user
    from courses.models import Course

    c = Course.objects.create(owner=t, title="C1")
    a = Assignment.objects.create(
        course=c,
        type=AssignmentType.PAPER,
        title="Paper",
        is_published=True,
        attempts_allowed=2,
        attempts_policy=Assignment.AttemptsPolicy.LATEST,
        max_marks=100.0,
    )
    Enrolment.objects.create(course=c, student=s)

    att1 = Attempt.objects.create(
        assignment=a, student=s, attempt_no=1, marks_awarded=40.0, released=True
    )
    att2 = Attempt.objects.create(
        assignment=a, student=s, attempt_no=2, marks_awarded=60.0, released=True
    )

    # Ensure initial grade prefers latest under LATEST policy
    Grade.objects.filter(assignment=a, student=s).delete()

    client.force_login(t)
    url = reverse("assignments:manage", args=[a.pk])
    # Post meta update switching to BEST; keep attempts_allowed valid (>= used)
    r = client.post(
        url,
        data={
            "action": "update_meta",
            "title": a.title,
            "instructions": "",
            "attempts_allowed": 2,
            "max_marks": 100,
            "attempts_policy": Assignment.AttemptsPolicy.BEST,
        },
    )
    assert r.status_code == 302 and r.headers["Location"].endswith(url)

    g = Grade.objects.filter(assignment=a, student=s).first()
    # BEST policy should choose the higher marks (60)
    assert g is not None and float(g.achieved_marks) == pytest.approx(60.0)


@pytest.mark.django_db
def test_quiz_unpublish_blocked_when_attempt_exists(client, make_quiz, teacher_user, student_user):
    a = make_quiz(owner=teacher_user, nq=1, nc=2)
    a.is_published = True
    a.save(update_fields=["is_published"])
    # Create attempt to lock
    Enrolment.objects.create(course=a.course, student=student_user)
    Attempt.objects.create(assignment=a, student=student_user, attempt_no=1)

    client.force_login(teacher_user)
    url = reverse("assignments:quiz-manage", args=[a.pk])
    r = client.post(url, data={"action": "unpublish"}, follow=True)
    a.refresh_from_db()
    assert r.status_code == 200
    assert a.is_published is True  # still published


@pytest.mark.django_db
def test_generic_unpublish_allowed_when_no_attempts(client, teacher_user):
    from courses.models import Course

    c = Course.objects.create(owner=teacher_user, title="C2")
    a = Assignment.objects.create(course=c, type=AssignmentType.PAPER, title="P", is_published=True)
    client.force_login(teacher_user)
    url = reverse("assignments:manage", args=[a.pk])
    r = client.post(url, data={"action": "unpublish"})
    assert r.status_code == 302 and r.headers["Location"].endswith(url)
    a.refresh_from_db()
    assert a.is_published is False
