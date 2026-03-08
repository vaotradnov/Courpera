from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_swagger_and_redoc_pages_load(client):
    r1 = client.get("/docs/")
    assert r1.status_code == 200
    assert "Swagger UI" in r1.text
    r2 = client.get("/redoc/")
    assert r2.status_code == 200
    assert "Redoc" in r2.text or "redoc" in r2.text.lower()
