from __future__ import annotations

from django.contrib.auth.models import User
from django.test import Client

from activity.models import Notification
from courses.models import Course, Enrolment
from discussions.models import Question, Vote


def test_qna_permissions_and_flows(db):
    teacher = User.objects.create_user(username="tqna", password="pw")
    teacher.profile.role = "teacher"
    teacher.profile.save(update_fields=["role"])
    student = User.objects.create_user(username="sqna", password="pw")
    student.profile.role = "student"
    student.profile.save(update_fields=["role"])
    outsider = User.objects.create_user(username="xqna", password="pw")
    course = Course.objects.create(owner=teacher, title="QnA", description="")
    Enrolment.objects.create(course=course, student=student)

    c = Client()
    # outsider cannot access
    assert c.login(username="xqna", password="pw")
    r_forbidden = c.get(f"/discussions/course/{course.id}/")
    assert r_forbidden.status_code == 403

    # student can access and ask
    c.logout()
    assert c.login(username="sqna", password="pw")
    r_ok = c.get(f"/discussions/course/{course.id}/")
    assert r_ok.status_code == 200
    r_post = c.post(
        f"/discussions/course/{course.id}/",
        {"action": "ask", "title": "How?", "body": "Help"},
        follow=True,
    )
    assert r_post.status_code == 200
    assert Question.objects.filter(course=course, title="How?").exists()
    # Owner gets notified
    assert Notification.objects.filter(user=teacher, type=Notification.TYPE_QNA).exists()

    q = Question.objects.get(course=course, title="How?")
    # reply
    c.post(
        f"/discussions/course/{course.id}/",
        {"action": "reply", "question_id": q.id, "body": "Answer"},
        follow=True,
    )
    assert q.replies.count() == 1
    # upvote (unique)
    c.post(
        f"/discussions/course/{course.id}/", {"action": "upvote", "question_id": q.id}, follow=True
    )
    assert Vote.objects.filter(question=q, user=student).count() == 1
    c.post(
        f"/discussions/course/{course.id}/", {"action": "upvote", "question_id": q.id}, follow=True
    )
    assert Vote.objects.filter(question=q, user=student).count() == 1

    # teacher can pin
    c.logout()
    assert c.login(username="tqna", password="pw")
    c.post(f"/discussions/course/{course.id}/", {"action": "pin", "question_id": q.id}, follow=True)
    q.refresh_from_db()
    assert q.pinned is True
