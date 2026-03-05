from __future__ import annotations


def test_security_headers_present_on_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Permissions-Policy" in r.headers
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
