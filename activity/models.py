"""Activity models: simple status updates (Stage 7)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Status(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="statuses"
    )
    text = models.CharField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id}:{self.text[:20]}"


class Notification(models.Model):
    TYPE_ENROLMENT = "enrolment"
    TYPE_MATERIAL = "material"
    TYPE_GRADE = "grade"
    TYPE_QNA = "qna"
    TYPE_CHOICES = (
        (TYPE_ENROLMENT, "Enrolment"),
        (TYPE_MATERIAL, "Material"),
        (TYPE_GRADE, "Grade"),
        (TYPE_QNA, "Q&A"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_actor",
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id}:{self.type}:{self.message[:20]}"
