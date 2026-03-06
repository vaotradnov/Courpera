from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

from courses.models import Course


class AssignmentType(models.TextChoices):
    QUIZ = "quiz", "Quiz"
    PAPER = "paper", "Paper"
    EXAM = "exam", "Exam"


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    type = models.CharField(max_length=16, choices=AssignmentType.choices)
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    # New: availability date/time when students can access the assignment
    available_from = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    # Stage 16.01: maximum marks for this assignment (used for grading)
    max_marks = models.FloatField(default=100.0)
    attempts_allowed = models.PositiveSmallIntegerField(default=1)

    class AttemptsPolicy(models.TextChoices):
        BEST = "best", "Best"
        LATEST = "latest", "Latest"

    # Stage 16.03: attempts policy determining aggregation across attempts
    attempts_policy = models.CharField(
        max_length=10,
        choices=AttemptsPolicy.choices,
        default=AttemptsPolicy.LATEST,
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["course", "is_published", "deadline"]),
        ]

    if TYPE_CHECKING:
        # Set dynamically in views for convenience; declared here for type checking
        ready_info: Optional[dict[str, Any]]
        avail_ok: bool
        attempts_used: int
        attempts_left: int

    def __str__(self) -> str:
        return f"{self.title} ({self.get_type_display()})"

    def is_open(self) -> bool:
        if not self.deadline:
            return True
        return timezone.now() < self.deadline

    def is_available(self) -> bool:
        """Whether the assignment is available to students based on availability time.

        Returns True if `available_from` is not set or the current time is
        after the availability start.
        """
        if not self.available_from:
            return True
        return timezone.now() >= self.available_from


class QuizQuestion(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField(default=0)
    text = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"Q{self.order}: {self.text[:40]}"

    if TYPE_CHECKING:
        # Annotated for mypy; populated in views
        choice_count: int
        correct_count: int


class QuizAnswerChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    order = models.PositiveSmallIntegerField(default=0)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    # Stage 16.03: optional explanation shown in feedback after attempt
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        # Use a simple, readable marker for correct choices.
        return f"Choice {self.order} (✓)" if self.is_correct else f"Choice {self.order}"


class Attempt(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_attempts"
    )
    attempt_no = models.PositiveSmallIntegerField(default=1)
    submitted_at = models.DateTimeField(default=timezone.now)
    score = models.FloatField(null=True, blank=True)
    # Stage 16.01: marking fields
    marks_awarded = models.FloatField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graded_attempts",
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    feedback_text = models.TextField(blank=True)
    override_reason = models.TextField(blank=True)
    released = models.BooleanField(default=False, db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["assignment", "student"]),
            models.Index(fields=["released", "assignment"]),
        ]

    def __str__(self) -> str:
        return f"Attempt {self.attempt_no} by {self.student_id} on {self.assignment_id}"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    choice = models.ForeignKey(QuizAnswerChoice, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("attempt", "question")


class StudentTextAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="text_answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    text = models.TextField()


class StudentFileSubmission(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="file_submissions")
    file = models.FileField(upload_to="assignment_submissions/")


class Grade(models.Model):
    """A per-student grade record for an assignment.

    This is kept in sync on submission/release and is used for fast
    gradebook queries and course percentage calculations.
    """

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="grades")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grades"
    )
    attempt = models.ForeignKey(
        Attempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="grade_records"
    )
    achieved_marks = models.FloatField(default=0.0)
    max_marks = models.FloatField(default=100.0)
    released_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("assignment", "student")
        indexes = [
            models.Index(fields=["assignment", "student"]),
            models.Index(fields=["course", "student"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="grade_marks_nonnegative",
                condition=models.Q(achieved_marks__gte=0.0) & models.Q(max_marks__gte=0.0),
            ),
            models.CheckConstraint(
                name="grade_marks_le_max",
                condition=models.Q(achieved_marks__lte=models.F("max_marks")),
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"Grade {self.student_id}/{self.assignment_id}: {self.achieved_marks}/{self.max_marks}"
        )
