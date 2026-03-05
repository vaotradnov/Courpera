from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """App configuration for real-time messaging (Channels)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "messaging"
