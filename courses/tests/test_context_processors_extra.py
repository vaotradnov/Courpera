from __future__ import annotations

import types

from courses import context_processors as cp


class _Q:
    def exclude(self, **kw):  # pragma: no cover
        raise RuntimeError("boom")


def test_course_subjects_handles_db_exception(monkeypatch):
    # Force the queryset build to raise to exercise except path
    monkeypatch.setattr(cp, "Course", types.SimpleNamespace(objects=_Q()))
    out = cp.course_subjects(object())
    assert "course_subjects" in out and isinstance(out["course_subjects"], list)
