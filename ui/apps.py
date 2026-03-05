from django.apps import AppConfig


class UiConfig(AppConfig):
    """App configuration for the UI layer.

    Keeping the config explicit simplifies discovery and avoids
    misconfiguration when more apps are added in later stages.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "ui"
