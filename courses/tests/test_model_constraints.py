from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from courses.models import Course, Enrolment
from courses.models_feedback import Feedback


@pytest.mark.django_db
def test_enrolment_unique_constraint_raises_integrity_error():
    t = User.objects.create_user(username="tuc", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="suc", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="UQ", description="")

    Enrolment.objects.create(course=course, student=s)
    with pytest.raises(IntegrityError):
        Enrolment.objects.create(course=course, student=s)


@pytest.mark.django_db
def test_feedback_unique_per_course_student():
    t = User.objects.create_user(username="tuf", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="suf", password="pw")
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="UF", description="")

    Feedback.objects.create(course=course, student=s, rating=4, comment="ok")
    with pytest.raises(IntegrityError):
        Feedback.objects.create(course=course, student=s, rating=5, comment="dup")
