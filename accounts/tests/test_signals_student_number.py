from __future__ import annotations

from django.contrib.auth.models import User

from accounts.models import Role, UserProfile
from accounts.signals import ensure_student_number


def test_ensure_student_number_assigns_when_missing(db):
    u = User.objects.create_user(username="s1", password="pw")
    p = UserProfile(user=u, role=Role.STUDENT, student_number="")
    ensure_student_number(sender=UserProfile, instance=p)
    assert p.student_number.startswith("S") and p.student_number[1:].isdigit()
