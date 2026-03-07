from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from django.utils import timezone

from messaging.consumers import _get_room_slow_mode
from messaging.models import Room


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_get_room_slow_mode_clears_expired():
    from asgiref.sync import sync_to_async

    r = await sync_to_async(Room.objects.create)(
        kind=Room.KIND_GROUP, title="g1", slow_mode_seconds=5
    )
    # No expiry set: returns current value
    v1 = await _get_room_slow_mode(r.id)
    assert v1 == 5

    # Expire in the past; helper should auto-clear and return 0
    r.slow_mode_expires_at = timezone.now() - timedelta(seconds=1)
    await sync_to_async(r.save)(update_fields=["slow_mode_expires_at"])
    v2 = await _get_room_slow_mode(r.id)
    assert v2 == 0
    await sync_to_async(r.refresh_from_db)()
    assert r.slow_mode_seconds == 0
