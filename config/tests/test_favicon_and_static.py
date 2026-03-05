from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_favicon_served_inline_svg():
    c = Client()
    r = c.get("/favicon.ico")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("image/svg+xml")
