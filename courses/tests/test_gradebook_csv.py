from __future__ import annotations

import csv
from io import StringIO

from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from assignments.models import Assignment, AssignmentType, Attempt, Grade
from courses.models import Course, Enrolment


def test_gradebook_csv_downloads_and_has_headers(db):
    # Setup teacher, students, course
    t = User.objects.create_user(username="teach_csv", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s1 = User.objects.create_user(username="stu1_csv", password="pw")
    s1.profile.role = "student"
    s1.profile.save(update_fields=["role"])
    s2 = User.objects.create_user(username="stu2_csv", password="pw")
    s2.profile.role = "student"
    s2.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="CSV Course", description="")
    Enrolment.objects.create(course=c, student=s1)
    Enrolment.objects.create(course=c, student=s2)

    a = Assignment.objects.create(
        course=c,
        type=AssignmentType.QUIZ,
        title="Quiz 1",
        is_published=True,
        available_from=timezone.now(),
    )
    # Create attempts and grades (quiz auto-release via upsert logic)
    att1 = Attempt.objects.create(assignment=a, student=s1, score=80.0)
    Grade.objects.create(
        assignment=a,
        course=c,
        student=s1,
        attempt=att1,
        achieved_marks=80.0,
        max_marks=100.0,
        released_at=timezone.now(),
    )
    att2 = Attempt.objects.create(assignment=a, student=s2, score=60.0)
    Grade.objects.create(
        assignment=a,
        course=c,
        student=s2,
        attempt=att2,
        achieved_marks=60.0,
        max_marks=100.0,
        released_at=timezone.now(),
    )

    client = Client()
    assert client.login(username="teach_csv", password="pw")
    resp = client.get(f"/courses/{c.id}/gradebook.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp["Content-Type"]
    assert "attachment; filename=" in resp["Content-Disposition"]

    # Basic CSV shape: headers include course percent
    data = resp.content.decode("utf-8")
    sio = StringIO(data)
    reader = csv.reader(sio)
    headers = next(reader)
    assert "username" in [h.lower() for h in headers]
    assert any("course %" in h.lower() for h in headers)
