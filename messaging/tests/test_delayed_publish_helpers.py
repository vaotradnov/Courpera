from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from messaging.consumer_helpers import (
    create_delayed_message,
    fetch_and_publish_due,
    mark_published,
)
from messaging.models import Message, Room


def test_delayed_publish_helpers_round_trip(db):
    # Setup: room and user
    u = User.objects.create_user(username="u1", password="pw")
    r = Room.objects.create(kind=Room.KIND_GROUP, title="g1")

    # Create delayed message scheduled in future
    mid = create_delayed_message(r.id, u.id, "hello world", None, delay_secs=1)
    m = Message.objects.get(pk=mid)
    assert m.visible_at > timezone.now()

    # Make it due by moving visible_at into the past
    m.visible_at = timezone.now() - timedelta(seconds=1)
    m.save(update_fields=["visible_at"])

    # Publish due messages and validate payload
    payloads = fetch_and_publish_due(r.id, limit=10)
    assert any(p.get("id") == mid for p in payloads)
    m.refresh_from_db()
    assert m.published_at is not None

    # Idempotent publish if called again
    mark_published(mid)
    m.refresh_from_db()
    assert m.published_at is not None
