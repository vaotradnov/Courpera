from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from assignments.models import Assignment, AssignmentType, Attempt
from assignments.services_manage import (
    add_question,
    delete_question,
    publish_assignment,
    unpublish_assignment_if_no_attempts,
    update_question_text,
)
from courses.models import Course


@pytest.mark.django_db
def test_publish_and_unpublish_guards():
    t = User.objects.create_user(username="tmh", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C")
    a = Assignment.objects.create(course=c, type=AssignmentType.EXAM, title="E1")

    assert not a.is_published and not a.deadline and not a.available_from
    publish_assignment(a)
    a.refresh_from_db()
    assert a.is_published and a.available_from and a.deadline
    assert a.deadline - a.available_from >= timedelta(days=7) - timedelta(seconds=1)

    # Unpublish allowed when no attempts
    assert unpublish_assignment_if_no_attempts(a) is True
    a.refresh_from_db()
    assert a.is_published is False

    # Unpublish blocked when attempts exist
    a.is_published = True
    a.save(update_fields=["is_published"])
    Attempt.objects.create(assignment=a, student=t)
    assert unpublish_assignment_if_no_attempts(a) is False


@pytest.mark.django_db
def test_question_add_update_delete():
    t = User.objects.create_user(username="tq", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C2")
    a = Assignment.objects.create(course=c, type=AssignmentType.EXAM, title="E2")

    q = add_question(a, "What is X?")
    assert q and q.assignment_id == a.id
    assert update_question_text(a, q.id, "Updated?") is True
    assert delete_question(a, q.id) is True
