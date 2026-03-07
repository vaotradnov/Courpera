from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User

from messaging import services
from messaging.models import Message, Room, RoomMembership


@pytest.mark.django_db
def test_create_chat_notifications_handles_metrics_and_logging_exceptions(monkeypatch):
    # Prepare DM room with two members (recipient exists)
    a = User.objects.create_user(username="a", password="pw")
    b = User.objects.create_user(username="b", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM)
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)
    m = Message.objects.create(room=room, sender=a, text="hi")

    # Make metrics_inc raise
    monkeypatch.setattr(
        "messaging.services.metrics_inc",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    # Make logger.info raise
    class BadLogger:
        def info(self, *a: Any, **k: Any):
            raise RuntimeError("boom")

    _orig_getlogger = services.logging.getLogger

    def _getlogger(name: str | None = None):
        if name == "courpera.notifications":
            return BadLogger()
        return _orig_getlogger(name)

    monkeypatch.setattr(services.logging, "getLogger", _getlogger)

    # Dummy channel layer that accepts group_send
    class DummyLayer:
        async def group_send(self, group: str, payload: dict[str, Any]):
            return None

    monkeypatch.setattr("messaging.services.get_channel_layer", lambda: DummyLayer())

    # Should not raise despite injected exceptions
    n = services.create_chat_notifications_for_message(m)
    assert n >= 1


@pytest.mark.django_db
def test_create_chat_notifications_handles_channel_layer_exception(monkeypatch):
    a = User.objects.create_user(username="a", password="pw")
    b = User.objects.create_user(username="b", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM)
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)
    m = Message.objects.create(room=room, sender=a, text="hi")

    # Raise when acquiring channel layer to exercise outer except
    monkeypatch.setattr(
        "messaging.services.get_channel_layer",
        lambda: (_ for _ in ()).throw(RuntimeError("no layer")),
    )

    n = services.create_chat_notifications_for_message(m)
    assert n >= 1


@pytest.mark.django_db
def test_notify_message_by_id_handles_metrics_exception(monkeypatch):
    a = User.objects.create_user(username="a", password="pw")
    b = User.objects.create_user(username="b", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM)
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)
    m = Message.objects.create(room=room, sender=a, text="hi")

    monkeypatch.setattr(
        "messaging.services.metrics_inc",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    # Also neutralize channel layer
    class DummyLayer:
        async def group_send(self, group: str, payload: dict[str, Any]):
            return None

    monkeypatch.setattr("messaging.services.get_channel_layer", lambda: DummyLayer())

    n = services.notify_message_by_id(m.id)
    assert n >= 1
