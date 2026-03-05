from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from assignments.templatetags.assign_utils import filesize, get_item, time_until


def test_get_item_with_non_mapping_returns_none():
    assert get_item(123, "key") is None


@pytest.mark.parametrize(
    "num, expected",
    [
        (0, "0 B"),
        (1, "1 B"),
        (1024, "1.0 KB"),
    ],
)
def test_filesize_boundaries(num, expected):
    assert filesize(num) == expected


def test_time_until_exception_fallback():
    # Passing a non-datetime object should return empty string gracefully
    assert time_until("not-a-datetime") == ""
    # Smoke: for a very near future date we get something non-empty
    dt = timezone.now() + timedelta(minutes=2)
    out = time_until(dt)
    assert isinstance(out, str) and out != ""
