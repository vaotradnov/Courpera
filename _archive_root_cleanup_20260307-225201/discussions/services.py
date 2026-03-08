from __future__ import annotations

from django.core.exceptions import PermissionDenied

from activity.models import Notification
from courses.models import Course, Enrolment

from .models import Question, Reply, Vote


def can_participate(user, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if course.owner_id == getattr(user, "id", None):
        return True
    return Enrolment.objects.filter(course=course, student=user).exists()


def create_question(course: Course, author, title: str, body: str | None = None) -> Question:
    q = Question.objects.create(course=course, author=author, title=title, body=body or "")
    Notification.objects.create(
        user=course.owner,
        actor=author,
        type=Notification.TYPE_QNA,
        course=course,
        message=f"New question: {title}",
    )
    return q


def add_reply(question: Question, author, body: str) -> Reply:
    r = Reply.objects.create(question=question, author=author, body=body)
    Notification.objects.create(
        user=question.course.owner,
        actor=author,
        type=Notification.TYPE_QNA,
        course=question.course,
        message=f"New reply on: {question.title}",
    )
    return r


def upvote_question(question: Question, user) -> bool:
    try:
        _, created = Vote.objects.get_or_create(question=question, user=user)
        return created
    except Exception:
        return False


def toggle_pin(question: Question, requester) -> bool:
    if question.course.owner_id != getattr(requester, "id", None):
        raise PermissionDenied
    question.pinned = not question.pinned
    question.save(update_fields=["pinned"])
    return question.pinned
