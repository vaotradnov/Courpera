from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext

from assignments.models import Assignment, AssignmentType, QuizAnswerChoice, QuizQuestion
from courses.models import Course, Enrolment


@pytest.mark.django_db
def test_take_quiz_query_budget_prefetch_choices(client):
    # Setup teacher, student, course, quiz with a few questions/choices
    teacher = User.objects.create_user(username="t", password="pw")
    student = User.objects.create_user(username="s", password="pw")
    c = Course.objects.create(owner=teacher, title="C")
    Enrolment.objects.create(course=c, student=student)
    a = Assignment.objects.create(course=c, type=AssignmentType.QUIZ, title="Q1", is_published=True)
    # 3 questions x 3 choices, 1 correct each
    for i in range(3):
        q = QuizQuestion.objects.create(assignment=a, order=i + 1, text=f"Q{i + 1}")
        for j in range(3):
            QuizAnswerChoice.objects.create(
                question=q, order=j + 1, text=f"C{j + 1}", is_correct=(j == 1)
            )

    assert client.login(username="s", password="pw")
    url = f"/assignments/{a.id}/take/"
    with CaptureQueriesContext(connection) as ctx:
        r = client.get(url)
    assert r.status_code == 200
    # Ensure queries are kept reasonable (prefetch used); allow slight variance across backends
    assert len(ctx.captured_queries) <= 14
