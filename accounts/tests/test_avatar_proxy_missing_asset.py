from __future__ import annotations

import pytest


@pytest.mark.django_db
def test_avatar_proxy_missing_asset_returns_400(client, monkeypatch):
    from django.contrib.staticfiles import finders

    # Force finders.find to return None to simulate missing file
    monkeypatch.setattr(finders, "find", lambda *_args, **_kwargs: None)
    # Valid size within range
    r = client.get("/accounts/avatar/1/64/")
    assert r.status_code == 400
