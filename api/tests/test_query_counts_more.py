from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext

from courses.models import Course, Enrolment
from materials.models import Material


@pytest.mark.django_db
@pytest.mark.performance
class TestMoreQueryCounts(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="tqc2", password="pw")
        self.teacher.profile.role = "teacher"
        self.teacher.profile.save(update_fields=["role"])
        self.student = User.objects.create_user(username="sqc2", password="pw")
        self.student.profile.role = "student"
        self.student.profile.save(update_fields=["role"])
        # Course with a few materials
        self.course = Course.objects.create(owner=self.teacher, title="Q", description="")
        Enrolment.objects.create(course=self.course, student=self.student)
        from django.core.files.uploadedfile import SimpleUploadedFile

        for i in range(3):
            f = SimpleUploadedFile(f"m{i}.pdf", b"%PDF-1.4\n", content_type="application/pdf")
            Material.objects.create(
                course=self.course, uploaded_by=self.teacher, title=f"M{i}", file=f
            )

    def test_materials_list_query_budget_student(self):
        c = Client()
        assert c.login(username="sqc2", password="pw")
        with CaptureQueriesContext(connection) as ctx:
            r = c.get("/api/v1/materials/")
            assert r.status_code == 200
        # count + select + auth/session overhead kept modest
        assert len(ctx.captured_queries) <= 5
