from django.apps import AppConfig


class ActivityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "activity"

    def ready(self) -> None:  # pragma: no cover
        from . import signals  # noqa: F401

        return super().ready()
