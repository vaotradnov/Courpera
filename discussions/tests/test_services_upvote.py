from __future__ import annotations

import types

from django.contrib.auth.models import User

from courses.models import Course
from discussions import services as ds
from discussions.models import Question


def test_upvote_question_second_time_returns_false(db):
    t = User.objects.create_user(username="teachq", password="pw")
    s = User.objects.create_user(username="stuq", password="pw")
    c = Course.objects.create(owner=t, title="C")
    q = Question.objects.create(course=c, author=s, title="Q")
    assert ds.upvote_question(q, s) is True
    assert ds.upvote_question(q, s) is False


def test_upvote_question_exception_returns_false(monkeypatch, db):
    t = User.objects.create_user(username="teachq2", password="pw")
    s = User.objects.create_user(username="stuq2", password="pw")
    c = Course.objects.create(owner=t, title="C2")
    q = Question.objects.create(course=c, author=s, title="Q2")

    class BadMgr:
        def get_or_create(self, **kw):  # pragma: no cover - exercise except path
            raise RuntimeError("boom")

    monkeypatch.setattr(ds, "Vote", types.SimpleNamespace(objects=BadMgr()))
    assert ds.upvote_question(q, s) is False
