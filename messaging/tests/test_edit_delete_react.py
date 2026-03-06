from __future__ import annotations

import asyncio
import json

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import Client

from config.asgi import application
from courses.models import Course, Enrolment
from messaging.models import Message, Room, RoomMembership


@database_sync_to_async
def _setup_env():
    teacher = User.objects.create_user(username="ed1", password="pw")
    student = User.objects.create_user(username="ed2", password="pw")
    c = Course.objects.create(owner=teacher, title="T", description="")
    Enrolment.objects.create(course=c, student=student)
    room = Room.objects.create(kind="course", course=c)
    return teacher.id, student.id, room.id


@database_sync_to_async
def _login_get_session(username: str, password: str) -> str:
    client = Client()
    assert client.login(username=username, password=password)
    return client.cookies.get("sessionid").value


@database_sync_to_async
def _http_post(url: str, sessionid: str, data: dict[str, str] | None = None):
    client = Client()
    client.cookies["sessionid"] = sessionid
    r = client.post(url, data or {})
    try:
        return r.status_code, json.loads(r.content)
    except Exception:
        return r.status_code, {}


@database_sync_to_async
def _http_delete(url: str, sessionid: str):
    client = Client()
    client.cookies["sessionid"] = sessionid
    r = client.delete(url)
    try:
        return r.status_code, json.loads(r.content)
    except Exception:
        return r.status_code, {}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.ws
async def test_message_edit_delete_and_reactions_ws_broadcasts():
    t_id, s_id, room_id = await _setup_env()
    sid_teacher = await _login_get_session("ed1", "pw")
    sid_student = await _login_get_session("ed2", "pw")
    # Connect WS as student
    comm = WebsocketCommunicator(
        application,
        f"/ws/chat/room/{room_id}/",
        headers=[(b"cookie", f"sessionid={sid_student}".encode())],
    )
    connected, _ = await comm.connect()
    assert connected

    # Create message via POST
    status, data = await _http_post(
        f"/messaging/rooms/{room_id}/messages/", sid_teacher, {"message": "hello"}
    )
    assert status == 200
    msg_id = data.get("id")
    payload = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert payload.get("type") == "message.new"
    assert payload.get("message") == "hello"

    # Edit
    status, _ = await _http_post(
        f"/messaging/messages/{msg_id}/", sid_teacher, {"message": "hello2"}
    )
    assert status == 200
    upd = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert upd.get("type") == "message.update"
    assert upd.get("message") == "hello2"

    # React add
    status, _ = await _http_post(
        f"/messaging/messages/{msg_id}/reactions/", sid_teacher, {"emoji": "👍"}
    )
    assert status == 200
    ra = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert ra.get("type") == "reaction.add"
    assert ra.get("message_id") == msg_id

    # React remove
    status, _ = await _http_delete(
        f"/messaging/messages/{msg_id}/reactions/?emoji=%F0%9F%91%8D", sid_teacher
    )
    assert status in (200, 204)
    rr = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert rr.get("type") == "reaction.remove"

    # Delete
    status, _ = await _http_post(f"/messaging/messages/{msg_id}/delete/", sid_teacher, {})
    assert status == 200
    dele = await asyncio.wait_for(comm.receive_json_from(), timeout=0.8)
    assert dele.get("type") == "message.delete"

    await comm.disconnect()


@pytest.mark.django_db
def test_thread_creation_via_parent_id_and_permissions():
    u1 = User.objects.create_user(username="th1", password="pw")
    u2 = User.objects.create_user(username="th2", password="pw")
    room = Room.objects.create(kind="group", title="G")
    RoomMembership.objects.create(room=room, user=u1, role="owner")
    RoomMembership.objects.create(room=room, user=u2, role="member")
    c1 = Client()
    assert c1.login(username="th1", password="pw")
    # Create parent
    r = c1.post(f"/messaging/rooms/{room.id}/messages/", {"message": "p"})
    pid = json.loads(r.content)["id"]
    # Reply
    r2 = c1.post(f"/messaging/rooms/{room.id}/messages/", {"message": "r", "parent_id": str(pid)})
    assert r2.status_code == 200
    mid = json.loads(r2.content)["id"]
    m = Message.objects.get(pk=mid)
    assert m.parent_message_id == pid
    # Non-member blocked
    outsider = User.objects.create_user(username="thx", password="pw")
    c2 = Client()
    assert c2.login(username="thx", password="pw")
    r3 = c2.post(f"/messaging/rooms/{room.id}/messages/", {"message": "nope"})
    assert r3.status_code == 403
