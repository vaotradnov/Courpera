from __future__ import annotations

import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.utils import timezone

from config.asgi import application
from courses.models import Course, Enrolment
from messaging.models import Room, RoomMembership


@database_sync_to_async
def _setup_presence_env():
    t = User.objects.create_user(username="pt1", password="pw")
    s = User.objects.create_user(username="pt2", password="pw")
    c = Course.objects.create(owner=t, title="P", description="")
    Enrolment.objects.create(course=c, student=s)
    room = Room.objects.create(kind="course", course=c)
    return t.id, s.id, room.id


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.ws
async def test_presence_and_typing_events_broadcast():
    t_id, s_id, room_id = await _setup_presence_env()

    # Auth sessions via Django test client to build cookies
    from django.test import Client

    @database_sync_to_async
    def _login(u, p):
        c = Client()
        assert c.login(username=u, password=p)
        return c.cookies.get("sessionid").value

    sid_t = await _login("pt1", "pw")
    sid_s = await _login("pt2", "pw")

    comm_t = WebsocketCommunicator(
        application,
        f"/ws/chat/room/{room_id}/",
        headers=[(b"cookie", f"sessionid={sid_t}".encode())],
    )
    connected, _ = await comm_t.connect()
    assert connected

    comm_s = WebsocketCommunicator(
        application,
        f"/ws/chat/room/{room_id}/",
        headers=[(b"cookie", f"sessionid={sid_s}".encode())],
    )
    connected, _ = await comm_s.connect()
    assert connected

    # One of them should receive a presence.state; don't assert exact count for portability
    try:
        evt = await asyncio.wait_for(comm_t.receive_json_from(), timeout=0.5)
        assert evt.get("type") == "presence.state"
    except Exception:
        # If timing skipped for t, s should have it
        evt2 = await asyncio.wait_for(comm_s.receive_json_from(), timeout=0.5)
        assert evt2.get("type") == "presence.state"

    # Typing from teacher should be visible to student
    await comm_t.send_json_to({"type": "typing", "action": "start"})
    evt = await asyncio.wait_for(comm_s.receive_json_from(), timeout=0.8)
    assert evt.get("type") == "typing.start"

    await comm_t.disconnect()
    await comm_s.disconnect()


@database_sync_to_async
def _setup_mute_env():
    owner = User.objects.create_user(username="mm1", password="pw")
    member = User.objects.create_user(username="mm2", password="pw")
    room = Room.objects.create(kind="group", title="G", slow_mode_seconds=2)
    RoomMembership.objects.create(room=room, user=owner, role="owner")
    RoomMembership.objects.create(room=room, user=member, role="member")
    return owner.id, member.id, room.id


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.ws
async def test_slow_mode_and_mute_blocks_messages():
    owner_id, member_id, room_id = await _setup_mute_env()

    from django.test import Client

    @database_sync_to_async
    def _login(u, p):
        c = Client()
        assert c.login(username=u, password=p)
        return c.cookies.get("sessionid").value

    sid_m = await _login("mm2", "pw")

    comm = WebsocketCommunicator(
        application,
        f"/ws/chat/room/{room_id}/",
        headers=[(b"cookie", f"sessionid={sid_m}".encode())],
    )
    ok, _ = await comm.connect()
    assert ok

    # First message allowed
    await comm.send_json_to({"message": "hi"})
    evt = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert evt.get("type") in ("message.new", "presence.state")
    if evt.get("type") == "presence.state":
        evt = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
        assert evt.get("type") == "message.new"

    # Second immediate message should hit slow-mode and return a system.notice
    await comm.send_json_to({"message": "hi2"})
    evt2 = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    # Could receive presence first depending on ordering; loop a bit to find the notice
    got_notice = evt2.get("type") == "system.notice"
    tries = 0
    while not got_notice and tries < 2:
        try:
            evt2 = await asyncio.wait_for(comm.receive_json_from(), timeout=0.4)
            got_notice = evt2.get("type") == "system.notice"
        except Exception:
            break
        tries += 1
    assert got_notice

    # Mute the member and ensure message is blocked
    @database_sync_to_async
    def _mute_member():
        mem = RoomMembership.objects.get(room_id=room_id, user_id=member_id)
        mem.muted_until = timezone.now() + timezone.timedelta(seconds=30)
        mem.save(update_fields=["muted_until"])

    await _mute_member()
    await comm.send_json_to({"message": "muted?"})
    evt3 = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert evt3.get("type") == "system.notice"

    await comm.disconnect()
