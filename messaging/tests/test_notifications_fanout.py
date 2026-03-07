from __future__ import annotations

import types

import pytest
from django.contrib.auth.models import User

from activity.models import Notification
from courses.models import Course, Enrolment
from messaging.models import Message, Room, RoomMembership
from messaging.services import create_chat_notifications_for_message


class DummyLayer:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def group_send(self, group: str, payload: dict):
        self.calls.append((group, payload))


@pytest.mark.django_db
def test_fanout_for_course_room_excludes_sender(monkeypatch):
    # Teacher (owner) and one enrolled student; student sends a message
    teacher = User.objects.create_user(username="teach", password="pw")
    student = User.objects.create_user(username="stud", password="pw")
    course = Course.objects.create(owner=teacher, title="C", description="")
    Enrolment.objects.create(course=course, student=student)
    room = Room.objects.create(kind=Room.KIND_COURSE, course=course, title="")

    # Prepare dummy channel layer to capture bumps
    layer = DummyLayer()

    def _get_layer():
        return layer

    monkeypatch.setattr("messaging.services.get_channel_layer", _get_layer)

    m = Message.objects.create(room=room, sender=student, text="hello")
    create_chat_notifications_for_message(m)

    # One recipient: the owner (sender is excluded)
    assert Notification.objects.filter(user=teacher, type=Notification.TYPE_CHAT).count() == 1
    assert Notification.objects.filter(user=student, type=Notification.TYPE_CHAT).count() == 0

    # One WS bump to the teacher group
    assert len(layer.calls) == 1
    grp, payload = layer.calls[0]
    assert grp == f"user_{teacher.id}_notifications"
    assert payload.get("payload", {}).get("type") == "notif.bump"


@pytest.mark.django_db
def test_fanout_for_dm_room_to_other_member(monkeypatch):
    a = User.objects.create_user(username="alice", password="pw")
    b = User.objects.create_user(username="bob", password="pw")
    room = Room.objects.create(kind=Room.KIND_DM, title="")
    RoomMembership.objects.create(room=room, user=a, role=RoomMembership.ROLE_OWNER)
    RoomMembership.objects.create(room=room, user=b, role=RoomMembership.ROLE_MEMBER)

    layer = DummyLayer()

    def _get_layer():
        return layer

    monkeypatch.setattr("messaging.services.get_channel_layer", _get_layer)

    m = Message.objects.create(room=room, sender=a, text="hi")
    create_chat_notifications_for_message(m)

    # Only Bob should receive one notification and one WS bump
    assert Notification.objects.filter(user=b, type=Notification.TYPE_CHAT).count() == 1
    assert Notification.objects.filter(user=a, type=Notification.TYPE_CHAT).count() == 0
    assert len(layer.calls) == 1
    grp, _ = layer.calls[0]
    assert grp == f"user_{b.id}_notifications"
