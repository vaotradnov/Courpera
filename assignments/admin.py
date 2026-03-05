from django.contrib import admin

from .models import (
    Assignment,
    Attempt,
    QuizAnswerChoice,
    QuizQuestion,
    StudentAnswer,
    StudentFileSubmission,
    StudentTextAnswer,
)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "type", "deadline", "attempts_allowed", "is_published")
    list_filter = ("type", "course", "is_published")
    search_fields = ("title", "course__title")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "order", "text")
    list_filter = ("assignment",)
    search_fields = ("text",)


@admin.register(QuizAnswerChoice)
class QuizAnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "text", "is_correct")
    list_filter = ("question", "is_correct")
    search_fields = ("text",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "attempt_no", "submitted_at", "score")
    list_filter = ("assignment",)
    search_fields = ("student__username",)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "choice")


@admin.register(StudentTextAnswer)
class StudentTextAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question")


@admin.register(StudentFileSubmission)
class StudentFileSubmissionAdmin(admin.ModelAdmin):
    list_display = ("attempt", "file")
