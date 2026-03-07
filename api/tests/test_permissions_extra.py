from __future__ import annotations

from types import SimpleNamespace

from api.permissions import IsStudent, IsTeacher


def test_is_teacher_and_is_student_false_for_anonymous():
    req = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    assert IsTeacher().has_permission(req, None) is False
    assert IsStudent().has_permission(req, None) is False
