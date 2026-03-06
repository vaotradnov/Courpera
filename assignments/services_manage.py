from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.db import models
from django.utils import timezone

from .models import Assignment, Attempt, QuizQuestion


def add_question(assignment: Assignment, text: str) -> Optional[QuizQuestion]:
    text = (text or "").strip()
    if not text:
        return None
    q = QuizQuestion(assignment=assignment, text=text)
    last = (assignment.questions.aggregate(models.Max("order")) or {}).get("order__max") or 0
    q.order = int(last) + 1
    q.save()
    return q


def update_question_text(assignment: Assignment, question_id: int, text: str) -> bool:
    q = assignment.questions.filter(pk=question_id).first()
    new = (text or "").strip()
    if q and new:
        q.text = new
        q.save(update_fields=["text"])
        return True
    return False


def delete_question(assignment: Assignment, question_id: int) -> bool:
    q = assignment.questions.filter(pk=question_id).first()
    if q:
        q.delete()
        return True
    return False


def publish_assignment(assignment: Assignment) -> None:
    if not assignment.available_from:
        assignment.available_from = timezone.now()
    if not assignment.deadline:
        base = assignment.available_from or timezone.now()
        assignment.deadline = base + timedelta(days=7)
    assignment.is_published = True
    assignment.save(update_fields=["available_from", "deadline", "is_published"])


def unpublish_assignment_if_no_attempts(assignment: Assignment) -> bool:
    if Attempt.objects.filter(assignment=assignment).exists():
        return False
    assignment.is_published = False
    assignment.save(update_fields=["is_published"])
    return True
