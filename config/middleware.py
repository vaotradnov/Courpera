from __future__ import annotations

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    """Add a minimal Content-Security-Policy header.

    Avoid inline scripts/styles to reduce XSS risk.
    """

    def process_response(self, request, response):  # noqa: D401
        # Base, strict policy applied site-wide
        style_src = "'self'"

        # Swagger UI injects one small inline <style> block. Allow it only on /docs/ via hash.
        # The hash value is taken from the browser CSP error suggestion.
        if request.path == "/docs/":
            style_src = (
                "'self' "
                "'sha256-RL3ie0nH+Lzz2YNqQN83mnU0J1ot4QL7b99vMdIX99w=' "  # pragma: allowlist secret
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


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add common security headers.

    - X-Content-Type-Options: nosniff
    - Permissions-Policy: disable sensitive features by default
    """

    def process_response(self, request, response):  # noqa: D401
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Minimal, privacy-friendly permissions policy
        perm = "geolocation=(), microphone=(), camera=(), payment=(), usb=(), fullscreen=(self)"
        response.setdefault("Permissions-Policy", perm)
        return response
