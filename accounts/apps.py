from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """App configuration for accounts (roles, profiles)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:  # pragma: no cover (import-time hook)
        # Import signal handlers to auto-create user profiles on user creation.
        from . import signals  # noqa: F401

        return super().ready()
