from __future__ import annotations

from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone

from courses.models import Course, Enrolment
from assignments.models import Assignment, AssignmentType, Grade


def test_student_grades_page_lists_percent(db):
    t = User.objects.create_user(username="teach_gpg", password="pw"); t.profile.role = "teacher"; t.profile.save(update_fields=["role"])
    s = User.objects.create_user(username="stud_gpg", password="pw"); s.profile.role = "student"; s.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=t, title="G Course", description="")
    Enrolment.objects.create(course=course, student=s)
    a = Assignment.objects.create(course=course, type=AssignmentType.QUIZ, title="Quiz", is_published=True, available_from=timezone.now(), max_marks=50)
    Grade.objects.create(assignment=a, course=course, student=s, achieved_marks=50, max_marks=50, released_at=timezone.now())

    c = Client(); assert c.login(username="stud_gpg", password="pw")
    resp = c.get("/accounts/grades/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="ignore")
    assert "Your Grades" in body and ("100%" in body or "100.0%" in body)
