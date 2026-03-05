from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from accounts.templatetags.avatar import avatar_url


@pytest.mark.django_db
def test_avatar_url_deterministic_and_size_param():
    u = User.objects.create_user(username="ava", password="pw")
    url1 = avatar_url(u, size=32)
    url2 = avatar_url(u, size=32)
    url3 = avatar_url(u, size=64)
    assert url1 == url2
    assert url1 != url3
    assert "size=32" in url1 and "size=64" in url3
    assert "seed=" in url1
