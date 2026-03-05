from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from assignments.models import AssignmentType


@pytest.mark.django_db
def test_quiz_quick_set_available_and_deadline_delta(client, make_quiz, teacher_user):
    a = make_quiz(owner=teacher_user, nq=1, nc=2)
    client.force_login(teacher_user)
    url = reverse("assignments:quiz-manage", args=[a.pk])

    # Quick set available now
    r1 = client.post(url, data={"action": "set_available_now"})
    assert r1.status_code == 302 and r1.headers["Location"].endswith(url)
    a.refresh_from_db()
    assert a.available_from is not None

    # Quick set deadline +1w (base defaults to now/available_from in view)
    before = timezone.now()
    r2 = client.post(url, data={"action": "set_deadline_delta", "deadline_delta": "1w"})
    assert r2.status_code == 302 and r2.headers["Location"].endswith(url)
    a.refresh_from_db()
    assert a.deadline is not None
    # Deadline should be roughly 7 days from now (+/- 2 minutes tolerance)
    delta = a.deadline - before
    assert 60 * 60 * 24 * 7 - 120 <= delta.total_seconds() <= 60 * 60 * 24 * 7 + 120


@pytest.mark.django_db
def test_quiz_update_question_redirects_with_anchor(client, make_quiz, teacher_user):
    a = make_quiz(owner=teacher_user, nq=1, nc=2)
    q = a.questions.first()
    client.force_login(teacher_user)
    url = reverse("assignments:quiz-manage", args=[a.pk])
    r = client.post(
        url, data={"action": "update_question", "question_id": q.id, "text": "New text"}
    )
    assert r.status_code == 302
    loc = r.headers.get("Location", "")
    assert f"?expand=q{q.id}#q{q.id}-edit" in loc


@pytest.mark.django_db
def test_assignment_manage_publish_sets_default_dates(client, make_quiz, teacher_user):
    # Use a non-quiz assignment managed by generic manage view
    a = make_quiz(owner=teacher_user)
    a.type = AssignmentType.PAPER
    a.available_from = None
    a.deadline = None
    a.is_published = False
    a.save(update_fields=["type", "available_from", "deadline", "is_published"])
    client.force_login(teacher_user)
    url = reverse("assignments:manage", args=[a.pk])
    r = client.post(url, data={"action": "publish"})
    assert r.status_code == 302 and r.headers["Location"].endswith(url)
    a.refresh_from_db()
    assert a.is_published is True
    assert a.available_from is not None and a.deadline is not None
    # Defaults: deadline = available_from + 7 days (+/- 2 minutes)
    delta = a.deadline - a.available_from
    assert 60 * 60 * 24 * 7 - 120 <= delta.total_seconds() <= 60 * 60 * 24 * 7 + 120
