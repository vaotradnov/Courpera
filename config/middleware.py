from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    """Add a basic Content-Security-Policy header.

    This policy avoids inline scripts/styles to reduce XSS risk. Inline
    styles in templates may be blocked; templates should prefer classes
    and external CSS/JS.
    """

    def process_response(self, request, response):  # noqa: D401
        # Base, strict policy applied site‑wide
        style_src = "'self'"

        # Swagger UI injects one small inline <style> block. Allow it only on /docs/ via hash.
        # The hash value is taken from the browser CSP error suggestion.
        if request.path == "/docs/":
            style_src = (
                "'self' "
                "'sha256-RL3ie0nH+Lzz2YNqQN83mnU0J1ot4QL7b99vMdIX99w=' "
                "'unsafe-hashes'"
            )

        csp = (
            "default-src 'self'; "
            "img-src 'self' https://api.dicebear.com data:; "
            "script-src 'self'; "
            f"style-src {style_src}; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )
        response["Content-Security-Policy"] = csp
        return response


class UserTimezoneMiddleware(MiddlewareMixin):
    """Activate per-user timezone (16.06).

    Defaults to settings.TIME_ZONE when profile has no preference.
    """

    def process_request(self, request):  # noqa: D401
        try:
            user = getattr(request, "user", None)
            tzname = None
            if user and getattr(user, "is_authenticated", False):
                prof = getattr(user, "profile", None)
                tzname = getattr(prof, "timezone", None)
            if tzname:
                timezone.activate(tzname)
            else:
                timezone.deactivate()  # fallback to default TIME_ZONE
        except Exception:
            pass
        return None
