"""Course feedback model (Stage 7)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .models import Course


class FeedbackManager(models.Manager["Feedback"]):
    pass


class Feedback(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course", "student"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="feedback_rating_range",
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
            )
        ]

    # Typed manager for better plugin inference
    objects: FeedbackManager = FeedbackManager()

    def __str__(self) -> str:  # pragma: no cover
        # Use related objects' primary keys to avoid mypy complaining about
        # auto-generated "_id" attributes on instances.
        return f"{self.course.pk}:{self.student.pk}={self.rating}"
