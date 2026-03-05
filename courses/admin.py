from django.contrib import admin

from .models import Course, Enrolment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title", "description", "owner__username")


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "completed", "created_at")
    list_filter = ("completed",)
    search_fields = ("course__title", "student__username")
