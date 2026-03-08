from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from activity.models import Status


@pytest.mark.django_db
def test_status_list_smoke(client):
    u = User.objects.create_user(username="alice", password="pw")
    Status.objects.create(user=u, text="Hello")
    r = client.get("/api/v1/status/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(item.get("text") == "Hello" for item in data)
