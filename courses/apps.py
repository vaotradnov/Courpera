from django.apps import AppConfig


class CoursesConfig(AppConfig):
    """App configuration for courses and enrolments."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "courses"
