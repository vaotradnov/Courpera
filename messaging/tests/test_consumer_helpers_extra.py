from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from messaging import consumer_helpers
from messaging.consumer_helpers import (
    create_delayed_message,
    fetch_and_publish_due,
    get_room_slow_mode,
)
from messaging.models import Message, Room


def test_get_room_slow_mode_nonexistent_returns_zero(db):
    assert get_room_slow_mode(999999) == 0


def test_create_delayed_message_truncates_text_over_500(db):
    u = User.objects.create_user(username="u1", password="pw")
    r = Room.objects.create(kind=Room.KIND_GROUP, title="g1")
    txt = "x" * 600
    mid = create_delayed_message(r.id, u.id, txt, None, delay_secs=1)
    m = Message.objects.get(pk=mid)
    assert len(m.text) == 500


def test_fetch_and_publish_due_handles_notification_error(monkeypatch, db):
    u = User.objects.create_user(username="u1", password="pw")
    r = Room.objects.create(kind=Room.KIND_GROUP, title="g1")
    m = Message.objects.create(
        room=r,
        sender=u,
        text="hi",
        visible_at=timezone.now() - timedelta(seconds=1),
    )

    # Force notify to raise, exercising the except path
    monkeypatch.setattr(
        "messaging.consumer_helpers.notify_message_by_id",
        lambda mid: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    out = fetch_and_publish_due(r.id, limit=10)
    assert any(p.get("id") == m.id for p in out)
