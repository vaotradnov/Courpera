from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from assignments.models import Assignment, AssignmentType, Attempt, Grade
from assignments.utils import upsert_grade_for_attempt
from courses.models import Course


def _course(owner: User, title: str = "C") -> Course:
    return Course.objects.create(owner=owner, title=title)


@pytest.mark.django_db
def test_upsert_quiz_attempt_computes_marks_and_auto_releases():
    t = User.objects.create_user(username="teach", password="pw")
    s = User.objects.create_user(username="stud", password="pw")
    c = _course(t)
    a = Assignment.objects.create(
        course=c, type=AssignmentType.QUIZ, title="Q", max_marks=50.0, is_published=True
    )

    att = Attempt.objects.create(assignment=a, student=s, attempt_no=1, score=60.0)
    g = upsert_grade_for_attempt(att, release=False)
    # score 60% of 50 = 30
    assert g.achieved_marks == 30.0
    assert g.max_marks == 50.0
    # quizzes auto-release
    assert g.released_at is not None
    att.refresh_from_db()
    assert att.released is True and att.released_at is not None


@pytest.mark.django_db
def test_upsert_paper_requires_release_flag_and_latest_policy():
    t = User.objects.create_user(username="teach2", password="pw")
    s = User.objects.create_user(username="stud2", password="pw")
    c = _course(t, "PaperC")
    a = Assignment.objects.create(
        course=c, type=AssignmentType.PAPER, title="P", max_marks=100.0, is_published=True
    )

    att1 = Attempt.objects.create(assignment=a, student=s, attempt_no=1)
    # No release -> not released
    g1 = upsert_grade_for_attempt(att1, release=False)
    assert g1.released_at is None
    att1.refresh_from_db()
    assert att1.released is False

    # Release the second attempt; latest policy uses the latest provided attempt
    att2 = Attempt.objects.create(assignment=a, student=s, attempt_no=2)
    g2 = upsert_grade_for_attempt(att2, release=True)
    assert g2.attempt_id == att2.id
    assert g2.released_at is not None
    att2.refresh_from_db()
    assert att2.released is True and att2.released_at is not None


@pytest.mark.django_db
def test_upsert_best_policy_does_not_downgrade():
    t = User.objects.create_user(username="teach3", password="pw")
    s = User.objects.create_user(username="stud3", password="pw")
    c = _course(t, "BestC")
    a = Assignment.objects.create(
        course=c,
        type=AssignmentType.QUIZ,
        title="QB",
        max_marks=100.0,
        is_published=True,
        attempts_policy=Assignment.AttemptsPolicy.BEST,
    )

    att_good = Attempt.objects.create(assignment=a, student=s, attempt_no=1, score=80.0)
    g = upsert_grade_for_attempt(att_good, release=False)
    assert g.achieved_marks == 80.0

    # Worse attempt submitted later should not reduce grade under BEST policy
    att_bad = Attempt.objects.create(assignment=a, student=s, attempt_no=2, score=40.0)
    g2 = upsert_grade_for_attempt(att_bad, release=False)
    assert g2.attempt_id == att_good.id
    assert g2.achieved_marks == 80.0
