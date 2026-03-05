from __future__ import annotations

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_url(request: HttpRequest, redirect_to: str | None) -> str | None:
    """Validate a next/redirect URL against the current host and scheme.

    Returns the URL if allowed, otherwise None.
    """
    if not redirect_to:
        return None
    if url_has_allowed_host_and_scheme(
        url=redirect_to, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect_to
    return None
