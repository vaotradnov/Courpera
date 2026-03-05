from __future__ import annotations

import pytest
from django.urls import reverse

from assignments.models import AssignmentType


@pytest.mark.django_db
def test_exam_manage_add_update_delete_question(client, make_quiz, teacher_user):
    # Create an exam with no attempts (unlocked)
    a = make_quiz(owner=teacher_user, nq=0)
    a.type = AssignmentType.EXAM
    a.is_published = False
    a.save(update_fields=["type", "is_published"])

    client.force_login(teacher_user)
    url = reverse("assignments:manage", args=[a.pk])

    # Add question
    r1 = client.post(url, data={"action": "add_question", "text": "What is polymorphism?"})
    assert r1.status_code == 302
    a.refresh_from_db()
    q = a.questions.first()
    assert q and q.text.startswith("What is polymorphism?")

    # Update question
    r2 = client.post(
        url, data={"action": "update_question", "question_id": q.id, "text": "Define polymorphism."}
    )
    assert r2.status_code == 302
    q.refresh_from_db()
    assert q.text == "Define polymorphism."

    # Delete question
    r3 = client.post(url, data={"action": "delete_question", "question_id": q.id})
    assert r3.status_code == 302
    assert a.questions.count() == 0
