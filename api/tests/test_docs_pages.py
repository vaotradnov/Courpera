from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_swagger_and_redoc_pages_load(client):
    r1 = client.get("/docs/")
    assert r1.status_code == 200
    # Template renders a swagger container element
    body1 = r1.content.decode()
    assert 'id="swagger-ui"' in body1

    r2 = client.get("/redoc/")
    assert r2.status_code == 200
    body2 = r2.content.decode()
    assert 'id="redoc-container"' in body2
