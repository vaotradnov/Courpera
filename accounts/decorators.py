"""Role-based access decorators."""

from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest


def role_required(*roles: str):
    """Require the current user to have one of the given roles.

    The decorator expects `request.user.profile.role` to be present.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            # Reject unauthenticated or missing profile early
            user = getattr(request, "user", None)
            if not getattr(user, "is_authenticated", False):
                raise PermissionDenied
            profile = getattr(user, "profile", None)
            role = getattr(profile, "role", None)
            if role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
