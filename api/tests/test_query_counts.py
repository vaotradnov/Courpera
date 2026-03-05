from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext

from courses.models import Course, Enrolment


@pytest.mark.django_db
@pytest.mark.performance
class TestQueryCounts(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="tqc", password="pw")
        self.teacher.profile.role = "teacher"
        self.teacher.profile.save(update_fields=["role"])
        # Create multiple courses for list view
        for i in range(5):
            Course.objects.create(owner=self.teacher, title=f"C{i}", description="")

    def test_courses_list_query_budget(self):
        c = Client()
        # Allow optimizations: assert query count does not exceed budget
        with CaptureQueriesContext(connection) as ctx:
            r = c.get("/api/v1/courses/")
            assert r.status_code == 200
        executed = len(ctx)
        if executed > 3:
            queries = "\n".join(f"{i + 1}. {q['sql']}" for i, q in enumerate(ctx.captured_queries))
            self.fail(
                f"{executed} queries executed, max allowed 3\nCaptured queries were:\n{queries}"
            )

    def test_enrolments_list_query_budget_student(self):
        student = User.objects.create_user(username="sqc", password="pw")
        student.profile.role = "student"
        student.profile.save(update_fields=["role"])
        # Enrol student into one course
        Enrolment.objects.create(course=Course.objects.first(), student=student)
        c = Client()
        assert c.login(username="sqc", password="pw")
        with self.assertNumQueries(5):  # allow a few for auth/session/select_related
            r = c.get("/api/v1/enrolments/")
            assert r.status_code == 200
