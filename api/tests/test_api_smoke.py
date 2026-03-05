from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role
from courses.models import Course


class ApiSmokeTests(TestCase):
    def setUp(self):
        # Create a teacher and a student with profiles/roles
        self.teacher = User.objects.create_user(username="t1", password="pw")
        self.teacher.profile.role = Role.TEACHER
        self.teacher.profile.save(update_fields=["role"])

        self.student = User.objects.create_user(username="s1", password="pw")
        self.student.profile.role = Role.STUDENT
        self.student.profile.save(update_fields=["role"])

        # Create a course owned by teacher
        self.course = Course.objects.create(owner=self.teacher, title="Demo", description="")
        self.client = APIClient()

    def test_schema_available(self):
        r = self.client.get("/api/schema/")
        assert r.status_code == 200

    def test_public_courses_list(self):
        r = self.client.get("/api/v1/courses/")
        assert r.status_code == 200

    def test_teacher_search_requires_teacher(self):
        # Student forbidden
        assert self.client.login(username="s1", password="pw")
        r = self.client.get("/api/v1/search/users", {"q": "s"})
        assert r.status_code == 403
        self.client.logout()

        # Teacher allowed
        assert self.client.login(username="t1", password="pw")
        r = self.client.get("/api/v1/search/users", {"q": "s"})
        assert r.status_code == 200

    def test_student_self_enrol_and_materials_filter(self):
        assert self.client.login(username="s1", password="pw")
        # Enrol
        r = self.client.post(
            "/api/v1/enrolments/",
            {"course": self.course.id, "completed": False},
            format="json",
        )
        assert r.status_code in (200, 201)

        # Materials filter by course should be 200 even if empty
        r = self.client.get(f"/api/v1/materials/?course={self.course.id}")
        assert r.status_code == 200
