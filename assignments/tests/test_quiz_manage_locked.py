from __future__ import annotations

import pytest
from django.urls import reverse

from assignments.models import AssignmentType, Attempt
from courses.models import Enrolment


@pytest.mark.django_db
def test_quiz_manage_locked_disallows_add_question(client, make_quiz, student_user, teacher_user):
    a = make_quiz(owner=teacher_user, nq=1, nc=2)
    # Create an attempt to lock structure
    Attempt.objects.create(assignment=a, student=student_user, attempt_no=1)
    client.force_login(teacher_user)
    url = reverse("assignments:quiz-manage", args=[a.pk])
    before = a.questions.count()
    r = client.post(url, data={"action": "add_question", "text": "New Q"})
    assert r.status_code == 200  # Falls through to render
    a.refresh_from_db()
    assert a.questions.count() == before


@pytest.mark.django_db
def test_assignment_manage_invalid_deadline_delta_shows_error(client, make_quiz, teacher_user):
    # Use generic manage with non-quiz type to hit invalid delta branch
    a = make_quiz(owner=teacher_user)
    a.type = AssignmentType.PAPER
    a.save(update_fields=["type"])
    client.force_login(teacher_user)
    url = reverse("assignments:manage", args=[a.pk])
    r = client.post(url, data={"action": "set_deadline_delta", "deadline_delta": "bogus"})
    assert r.status_code == 302
    # Deadline remains None
    a.refresh_from_db()
    assert a.deadline is None


@pytest.mark.django_db
def test_exam_text_submission_missing_and_success(client, make_quiz, student_user, teacher_user):
    # Turn quiz into exam with one question; exam uses text answers
    a = make_quiz(owner=teacher_user, nq=1, nc=2)
    a.type = AssignmentType.EXAM
    a.is_published = True
    a.save(update_fields=["type", "is_published"])
    client.force_login(student_user)
    take_url = reverse("assignments:take", args=[a.pk])
    submit_url = reverse("assignments:submit", args=[a.pk])
    # Enrol student
    Enrolment.objects.create(course=a.course, student=student_user)
    # Missing text -> error redirect to take
    r1 = client.post(submit_url, data={})
    assert r1.status_code == 302 and r1.headers.get("Location", "").endswith(take_url)
    # Provide text -> feedback redirect
    qid = a.questions.first().id
    r2 = client.post(submit_url, data={f"text_{qid}": "My answer"})
    assert r2.status_code == 302
    # Redirect endpoint is feedback URL for created attempt
    assert "/assignments/attempt/" in r2.headers.get("Location", "")
