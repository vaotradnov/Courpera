import logging

import pytest
from django.contrib.auth.models import User

from assignments.models import Assignment, AssignmentType, QuizAnswerChoice, QuizQuestion
from courses.models import Course


@pytest.fixture(autouse=True)
def silence_django_loggers():
    # Reduce noisy warnings in test output (e.g., CSRF rejections during negative tests)
    names = [
        "django.request",
        "django.security.csrf",
    ]
    originals = {}
    for name in names:
        logger = logging.getLogger(name)
        originals[name] = logger.level
        logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        for name in names:
            logging.getLogger(name).setLevel(originals.get(name, logging.WARNING))


@pytest.fixture()
def teacher_user(db):
    u = User.objects.create_user(username="teacher_fx", password="pw")  # pragma: allowlist secret
    try:
        p = u.profile
        p.role = "teacher"
        p.save(update_fields=["role"])
    except Exception:
        pass
    return u


@pytest.fixture()
def student_user(db):
    u = User.objects.create_user(username="student_fx", password="pw")  # pragma: allowlist secret
    try:
        p = u.profile
        p.role = "student"
        p.save(update_fields=["role"])
    except Exception:
        pass
    return u


@pytest.fixture()
def make_course(db, teacher_user):
    def _make_course(owner=None, title="Course FX"):
        return Course.objects.create(owner=owner or teacher_user, title=title)

    return _make_course


@pytest.fixture()
def make_quiz(db, make_course, teacher_user):
    def _make_quiz(owner=None, nq=1, nc=2, correct_index=1, title="Quiz FX"):
        c = make_course(owner=owner or teacher_user, title=f"{title} Course")
        a = Assignment.objects.create(
            course=c, type=AssignmentType.QUIZ, title=title, max_marks=100.0, is_published=True
        )
        for qi in range(nq):
            q = QuizQuestion.objects.create(assignment=a, order=qi + 1, text=f"Q{qi + 1}")
            for ci in range(nc):
                QuizAnswerChoice.objects.create(
                    question=q, order=ci + 1, text=f"C{ci + 1}", is_correct=(ci == correct_index)
                )
        return a

    return _make_quiz
