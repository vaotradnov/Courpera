from __future__ import annotations

import asyncio
import json

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client

from config.asgi import application
from courses.models import Course, Enrolment


@database_sync_to_async
def _setup_users_and_course():
    teacher = User.objects.create_user(username="tperm", password="pw")
    teacher.profile.role = "teacher"
    teacher.profile.save(update_fields=["role"])
    student = User.objects.create_user(username="sperm", password="pw")
    student.profile.role = "student"
    student.profile.save(update_fields=["role"])
    other = User.objects.create_user(username="xperm", password="pw")
    course = Course.objects.create(owner=teacher, title="P", description="")
    Enrolment.objects.create(course=course, student=student)
    return teacher.id, student.id, other.id, course.id


async def _connect_ws(course_id: int, sessionid: str):
    headers = [(b"cookie", f"sessionid={sessionid}".encode())]
    comm = WebsocketCommunicator(application, f"/ws/chat/course/{course_id}/", headers=headers)
    connected, _ = await comm.connect()
    return connected, comm


@database_sync_to_async
def _login_get_sessionid(username: str, password: str) -> str:
    c = Client()
    assert c.login(username=username, password=password)
    return c.cookies.get(settings.SESSION_COOKIE_NAME).value


@database_sync_to_async
def _http_get_history(course_id: int, sessionid: str):
    c = Client()
    c.cookies[settings.SESSION_COOKIE_NAME] = sessionid
    r = c.get(f"/messaging/course/{course_id}/history/")
    try:
        data = json.loads(r.content)
    except Exception:
        data = {}
    return r.status_code, data


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.ws
async def test_ws_permissions_and_history_endpoint():
    teacher_id, student_id, other_id, course_id = await _setup_users_and_course()

    # Build sessions for each user via Django test client (session auth) in a sync context
    sid_teacher = await _login_get_sessionid("tperm", "pw")
    sid_student = await _login_get_sessionid("sperm", "pw")
    sid_other = await _login_get_sessionid("xperm", "pw")

    # Owner can connect
    ok, comm_t = await _connect_ws(course_id, sid_teacher)
    assert ok
    await comm_t.send_json_to({"message": "hello"})
    await asyncio.sleep(0.05)
    await comm_t.disconnect()

    # Enrolled student can connect
    ok, comm_s = await _connect_ws(course_id, sid_student)
    assert ok
    await comm_s.disconnect()

    # Unenrolled user cannot connect
    ok, comm_x = await _connect_ws(course_id, sid_other)
    assert not ok
    await comm_x.disconnect()

    # History endpoint: owner and enrolled see messages; unenrolled 403
    status_owner, data_owner = await _http_get_history(course_id, sid_teacher)
    assert status_owner == 200
    assert any(item.get("message") == "hello" for item in data_owner.get("results", []))

    status_student, _ = await _http_get_history(course_id, sid_student)
    assert status_student == 200

    status_other, _ = await _http_get_history(course_id, sid_other)
    assert status_other == 403
