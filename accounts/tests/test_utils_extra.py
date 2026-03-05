from __future__ import annotations

from django.test import RequestFactory

from accounts.utils import safe_next_url


def test_safe_next_url_none_returns_none() -> None:
    rf = RequestFactory()
    req = rf.get("/")
    assert safe_next_url(req, None) is None
