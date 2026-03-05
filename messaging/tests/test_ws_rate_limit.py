from __future__ import annotations

import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import Client

from config.asgi import application
from courses.models import Course


@database_sync_to_async
def _setup_teacher_and_session():
    teacher = User.objects.create_user(username="tWS", password="pw")
    # Mark teacher role
    teacher.profile.role = "teacher"
    teacher.profile.save(update_fields=["role"])
    course = Course.objects.create(owner=teacher, title="WS", description="")
    client = Client()
    assert client.login(username="tWS", password="pw")
    sessionid = client.cookies.get("sessionid").value
    return course.id, sessionid


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.ws
async def test_ws_rate_limit_allows_up_to_five_messages():
    course_id, sessionid = await _setup_teacher_and_session()
    headers = [(b"cookie", f"sessionid={sessionid}".encode())]

    communicator = WebsocketCommunicator(
        application, f"/ws/chat/course/{course_id}/", headers=headers
    )
    connected, _ = await communicator.connect()
    assert connected

    # Send 6 quick messages; rate limiter should drop at least one
    for i in range(6):
        await communicator.send_json_to({"message": f"m{i}"})
    await asyncio.sleep(0.2)

    # Read echoes (up to a timeout)
    received = []
    try:
        while True:
            msg = await asyncio.wait_for(communicator.receive_json_from(), timeout=0.2)
            received.append(msg)
            if len(received) >= 6:
                break
    except Exception:
        pass

    await communicator.disconnect()
    # Expect at most 5 within the 5-second window
    assert len(received) <= 5
