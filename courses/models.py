"""Courses and enrolments models (Stage 5).

Defines a minimal `Course` owned by a teacher and an `Enrolment` linking
students to courses. Teacher removal is implemented by deleting the
enrolment record (simple and SQLite-friendly).
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Course(models.Model):
    """A course authored by a teacher user."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_courses")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Teacher-editable syllabus and outcomes (one item per line)
    syllabus = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    # 16.04: Catalogue metadata and thumbnail
    subject = models.CharField(max_length=100, blank=True)
    level = models.CharField(
        max_length=20,
        choices=(
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ),
        default="beginner",
    )
    language = models.CharField(max_length=50, default="English")
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.title}"

    def is_owner(self, user: User) -> bool:
        return bool(user and user.is_authenticated and self.owner_id == user.id)


class Enrolment(models.Model):
    """Link a student to a course.

    We enforce uniqueness at the application level. Deletion represents
    teacher removal; this keeps the schema simple for SQLite.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrolments")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrolments")
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student")
        ordering = ["course_id", "student_id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.student_id}->{self.course_id}"
