from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
@pytest.mark.security
def test_csp_header_present():
    c = Client()
    r = c.get("/")
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers


@pytest.mark.django_db
@pytest.mark.security
def test_openapi_schema_available():
    c = Client()
    r = c.get("/api/schema/")
    assert r.status_code == 200
    body = r.content.decode("utf-8", errors="ignore")
    assert "openapi" in body.lower()
