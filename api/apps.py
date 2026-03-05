from django.apps import AppConfig


class ApiConfig(AppConfig):
    """App configuration for the REST API layer."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
