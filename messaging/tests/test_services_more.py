from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from messaging.models import Message, Room, RoomMembership
from messaging.services import (
    _format_message,
    create_chat_notifications_for_message,
    notify_message_by_id,
)


@pytest.mark.django_db
def test_notifications_disabled_returns_zero(monkeypatch):
    a = User.objects.create_user(username="a", password="pw")
    b = User.objects.create_user(username="b", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM)
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)
    m = Message.objects.create(room=room, sender=a, text="hi")
    with override_settings(NOTIFICATIONS_IN_APP_ENABLED=False):
        assert create_chat_notifications_for_message(m) == 0


@pytest.mark.django_db
def test_recipients_for_course_room_without_course_is_empty():
    # Room is course kind but not bound to a Course -> no recipients
    a = User.objects.create_user(username="a", password="pw")
    room = Room.objects.create(kind=Room.KIND_COURSE)
    m = Message.objects.create(room=room, sender=a, text="hi")
    assert create_chat_notifications_for_message(m) == 0


@pytest.mark.django_db
def test_format_message_variants():
    u = User.objects.create_user(username="alice", password="pw")
    # Course
    r1 = Room.objects.create(kind=Room.KIND_COURSE, title="")
    m1 = Message.objects.create(room=r1, sender=u, text="x" * 45)
    s1 = _format_message(m1)
    assert s1.startswith("Course chat:") and s1.endswith("...")
    # Group
    r2 = Room.objects.create(kind=Room.KIND_GROUP, title="")
    m2 = Message.objects.create(room=r2, sender=u, text="hello")
    assert _format_message(m2).startswith("Group chat:")
    # DM
    r3 = Room.objects.create(kind=Room.KIND_DM, title="")
    m3 = Message.objects.create(room=r3, sender=u, text="")
    assert _format_message(m3).startswith("Direct chat:")


@pytest.mark.django_db
def test_notify_message_by_id_increments_created_counter(monkeypatch, client):
    # Setup DM members so recipients exist
    a = User.objects.create_user(username="a", password="pw")
    b = User.objects.create_user(username="b", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM)
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)

    # Use a dummy channel layer to avoid touching real ASGI layer
    class DummyLayer:
        async def group_send(self, group: str, payload: dict[str, Any]):
            return None

    monkeypatch.setattr("messaging.services.get_channel_layer", lambda: DummyLayer())

    m = Message.objects.create(room=room, sender=a, text="hi")
    before = client.get("/metrics").content.decode("utf-8")
    notify_message_by_id(m.id)
    after = client.get("/metrics").content.decode("utf-8")

    def _val(txt: str) -> int:
        for line in txt.splitlines():
            if line.startswith("courpera_messages_created_total "):
                return int(line.split()[-1])
        return 0

    assert _val(after) >= _val(before) + 1
