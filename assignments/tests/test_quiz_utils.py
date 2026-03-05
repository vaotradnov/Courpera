from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from assignments.models import (
    Assignment,
    AssignmentType,
    Attempt,
    Grade,
    QuizAnswerChoice,
    QuizQuestion,
)
from assignments.utils import grade_quiz, quiz_readiness, recalc_grades_for_assignment
from courses.models import Course


def _make_quiz(owner: User, title: str = "Quiz") -> Assignment:
    c = Course.objects.create(owner=owner, title=f"{title} Course")
    a = Assignment.objects.create(course=c, type=AssignmentType.QUIZ, title=title, max_marks=100.0)
    return a


@pytest.mark.django_db
def test_quiz_readiness_conditions():
    t = User.objects.create_user(username="teacher", password="pw")
    a = _make_quiz(t)

    # No questions
    info = quiz_readiness(a)
    assert info["ready"] is False and any("no questions" in s.lower() for s in info["issues"])

    # Add question with only one choice and not marked correct => two issues
    q1 = QuizQuestion.objects.create(assignment=a, order=1, text="Q1")
    c1 = QuizAnswerChoice.objects.create(question=q1, order=1, text="A")
    info = quiz_readiness(a)
    assert info["ready"] is False
    assert any("exactly one correct" in s.lower() for s in info["issues"])
    assert any("at least two" in s.lower() for s in info["issues"])

    # Fix choices count but mark two correct => still not ready
    c2 = QuizAnswerChoice.objects.create(question=q1, order=2, text="B", is_correct=True)
    c1.is_correct = True
    c1.save(update_fields=["is_correct"])
    info = quiz_readiness(a)
    assert info["ready"] is False and any(
        "exactly one correct" in s.lower() for s in info["issues"]
    )

    # Fix to exactly one correct => ready (with only one question)
    c1.is_correct = False
    c1.save(update_fields=["is_correct"])
    info = quiz_readiness(a)
    assert info["ready"] is True and info["issues"] == []


@pytest.mark.django_db
def test_grade_quiz_scoring_and_per_question():
    t = User.objects.create_user(username="teacher2", password="pw")
    a = _make_quiz(t, title="Quiz2")
    # Build 3 questions, each with two choices, mark the second correct
    correct_ids = {}
    for i in range(3):
        q = QuizQuestion.objects.create(assignment=a, order=i + 1, text=f"Q{i + 1}")
        QuizAnswerChoice.objects.create(question=q, order=1, text="Wrong")
        c = QuizAnswerChoice.objects.create(question=q, order=2, text="Right", is_correct=True)
        correct_ids[q.id] = c.id
    # Select 2 correct, 1 wrong
    selected = {}
    for idx, (qid, cid) in enumerate(correct_ids.items()):
        selected[qid] = cid if idx < 2 else 0  # last wrong
    result = grade_quiz(a, selected)
    assert result["total"] == 3
    assert result["correct"] == 2
    assert result["score"] == 66.67 or result["score"] == 66.66  # rounding tolerance
    # Per-question map has a boolean for each qid
    assert len([k for k, v in result["per_question"].items() if v]) == 2


@pytest.mark.django_db
def test_recalc_grades_best_vs_latest_policy():
    t = User.objects.create_user(username="teacher3", password="pw")
    s = User.objects.create_user(username="stud", password="pw")
    a = _make_quiz(t, title="Quiz3")
    # One question to compute % easily
    q = QuizQuestion.objects.create(assignment=a, order=1, text="Q1")
    ca = QuizAnswerChoice.objects.create(question=q, order=1, text="Right", is_correct=True)
    QuizAnswerChoice.objects.create(question=q, order=2, text="Wrong", is_correct=False)

    # Two attempts: 40% and 80% (marks computed from score)
    att1 = Attempt.objects.create(assignment=a, student=s, attempt_no=1, score=40.0)
    att2 = Attempt.objects.create(assignment=a, student=s, attempt_no=2, score=80.0)

    # Latest policy (default): grade reflects attempt 2
    a.attempts_policy = Assignment.AttemptsPolicy.LATEST
    a.save(update_fields=["attempts_policy"])
    recalc_grades_for_assignment(a)
    g = Grade.objects.get(assignment=a, student=s)
    assert g.attempt_id == att2.id
    assert g.achieved_marks == 80.0
    assert g.max_marks == 100.0
    assert g.released_at is not None  # quizzes auto-release

    # Switch to best: grade should not downgrade if existing grade is higher
    a.attempts_policy = Assignment.AttemptsPolicy.BEST
    a.save(update_fields=["attempts_policy"])
    att2.score = 30.0
    att2.marks_awarded = None  # force recompute branch
    att2.save(update_fields=["score", "marks_awarded"])
    recalc_grades_for_assignment(a)
    g2 = Grade.objects.get(assignment=a, student=s)
    # Still points to previous best (80) on att2 because we don't downgrade for BEST policy
    assert g2.attempt_id == att2.id
    assert g2.achieved_marks == 80.0

    # If att1 becomes better than current best, grade should upgrade to att1
    att1.score = 90.0
    att1.marks_awarded = None
    att1.save(update_fields=["score", "marks_awarded"])
    recalc_grades_for_assignment(a)
    g3 = Grade.objects.get(assignment=a, student=s)
    assert g3.attempt_id == att1.id
    assert g3.achieved_marks == 90.0
