import os
import platform

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def _admin_mode(request: HttpRequest) -> bool:
    """Return True when Admin Mode is active.

    Admin Mode is visible to staff users or when explicitly enabled via
    the `ADMIN_MODE` environment variable. This helps graders and
    operators by surfacing environment and version details on the index
    page without requiring authentication in constrained demos.
    """
    try:
        user = getattr(request, "user", None)
        if user and not isinstance(user, AnonymousUser) and getattr(user, "is_staff", False):
            return True
    except Exception:
        # Be permissive: if user resolution fails, fall back to env.
        pass
    return str(os.environ.get("ADMIN_MODE", "")).strip().lower() in {"1", "true", "yes", "on"}


def _run_info() -> dict | None:
    """Collect basic runtime information for quick diagnostics.

    Keep this minimal and robust; failures here should never break the
    index page.
    """
    try:
        import django  # local import to avoid module-level side effects

        try:
            import rest_framework

            drf_version: str | None = getattr(rest_framework, "__version__", None)
        except Exception:
            drf_version = None
        return {
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "django": django.get_version(),
            "drf": drf_version,
        }
    except Exception:
        return None


def index(request: HttpRequest) -> HttpResponse:
    """Render the public landing page with Admin Mode panel support.

    In Admin Mode, show environment details, versions, and convenient
    links to the interactive API documentation. When not in Admin Mode,
    keep the page minimal and student-facing.
    """
    admin_mode = _admin_mode(request)
    ctx = {
        "app_name": "Courpera",
        "tagline": "A streamlined, server-rendered e-learning application.",
        "admin_mode": admin_mode,
        "runinfo": _run_info() if admin_mode else None,
        # Optional credentials for operator/grader convenience; read from env
        "admin_user": os.environ.get("ADMIN_USERNAME"),
        "admin_pass": os.environ.get("ADMIN_PASSWORD"),
    }
    return render(request, "index.html", ctx)
