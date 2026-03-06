from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client

from courses.models import Course, Enrolment
from messaging.models import Room


@pytest.mark.django_db
def test_create_dm_and_fetch_history():
    u1 = User.objects.create_user(username="alice", password="pw")
    u2 = User.objects.create_user(username="bob", password="pw")

    c = Client()
    assert c.login(username="alice", password="pw")

    # Create DM by user id
    r = c.post("/messaging/rooms/dm/", {"user_id": u2.id})
    assert r.status_code == 200
    data = json.loads(r.content)
    room_id = data.get("room_id")
    assert isinstance(room_id, int)

    # Fetch DM history as member (empty ok)
    r2 = c.get(f"/messaging/rooms/{room_id}/messages/")
    assert r2.status_code == 200
    data2 = json.loads(r2.content)
    assert "results" in data2

    # Non-member should be forbidden
    c.logout()
    u3 = User.objects.create_user(username="charlie", password="pw")
    assert c.login(username="charlie", password="pw")
    r3 = c.get(f"/messaging/rooms/{room_id}/messages/")
    assert r3.status_code == 403


@pytest.mark.django_db
def test_create_group_and_permissions_history():
    owner = User.objects.create_user(username="owner", password="pw")
    member = User.objects.create_user(username="member", password="pw")

    c = Client()
    assert c.login(username="owner", password="pw")
    # Create group and add member
    r = c.post("/messaging/rooms/group/", {"title": "Study Group", "member_ids": str(member.id)})
    assert r.status_code == 200
    room_id = json.loads(r.content).get("room_id")
    assert isinstance(room_id, int)

    # Owner can fetch
    r2 = c.get(f"/messaging/rooms/{room_id}/messages/")
    assert r2.status_code == 200

    # Switch to member
    c.logout()
    assert c.login(username="member", password="pw")
    r3 = c.get(f"/messaging/rooms/{room_id}/messages/")
    assert r3.status_code == 200

    # Switch to non-member
    outsider = User.objects.create_user(username="outsider", password="pw")
    c.logout()
    assert c.login(username="outsider", password="pw")
    r4 = c.get(f"/messaging/rooms/{room_id}/messages/")
    assert r4.status_code == 403


@pytest.mark.django_db
def test_course_room_history_wrapper_uses_room_model():
    # Create course with owner and enrolled student
    owner = User.objects.create_user(username="teach", password="pw")
    student = User.objects.create_user(username="stud", password="pw")
    c = Course.objects.create(owner=owner, title="T", description="")
    Enrolment.objects.create(course=c, student=student)

    client = Client()
    assert client.login(username="stud", password="pw")

    # Ensure the course history endpoint creates/uses a Room(kind=course)
    r = client.get(f"/messaging/course/{c.id}/history/")
    assert r.status_code == 200
    # A Room should exist now
    room = Room.objects.filter(kind="course", course=c).first()
    assert room is not None
