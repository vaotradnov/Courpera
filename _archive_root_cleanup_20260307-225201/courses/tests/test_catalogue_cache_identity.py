from __future__ import annotations

from django.test import override_settings

from courses import views as course_views


def test_catalogue_cache_decorator_identity_when_disabled() -> None:
    # When CATALOGUE_CACHE_ENABLED=False, the decorator returns a passthrough.
    with override_settings(CATALOGUE_CACHE_ENABLED=False):
        dec = course_views._catalogue_cache_decorator()

    def sentinel(x: int) -> int:
        return x + 1

    wrapped = dec(sentinel)
    # Identity decorator should return the same function object
    assert wrapped is sentinel
    # And behavior unchanged
    assert wrapped(3) == 4
