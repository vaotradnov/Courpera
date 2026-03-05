from __future__ import annotations

from django.test import Client


def test_csp_no_unsafe_inline_on_root(client: Client):
    r = client.get("/")
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy", "")
    assert "unsafe-inline" not in csp
    assert "style-src 'self'" in csp


def test_csp_docs_allows_style_hash_only(client: Client):
    r = client.get("/docs/")
    assert r.status_code in (200, 302, 303)  # docs may redirect to swagger/redoc
    csp = r.headers.get("Content-Security-Policy", "")
    # hash allowance present
    assert "unsafe-inline" not in csp
    assert "sha256-" in csp
