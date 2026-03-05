from __future__ import annotations

from django.test import RequestFactory

from accounts.utils import safe_next_url


def test_safe_next_url_allows_same_host_https_and_relative():
    rf = RequestFactory()
    req = rf.get("/login/")
    # Simulate secure request
    req._is_secure_override = True
    req.is_secure = lambda: True  # type: ignore
    # Allowed: relative URL
    assert safe_next_url(req, "/accounts/home/") == "/accounts/home/"
    # Allowed: same host
    req.get_host = lambda: "testserver"  # type: ignore
    assert (
        safe_next_url(req, "https://testserver/accounts/home/")
        == "https://testserver/accounts/home/"
    )


def test_safe_next_url_rejects_external():
    rf = RequestFactory()
    req = rf.get("/login/")
    req.is_secure = lambda: False  # type: ignore
    req.get_host = lambda: "example.com"  # type: ignore
    assert safe_next_url(req, "http://evil.com/") is None
