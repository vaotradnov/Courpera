from __future__ import annotations

import io

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from messaging.models import Room, RoomMembership


@pytest.mark.django_db
def test_room_message_with_attachment_and_history_includes_attachment():
    owner = User.objects.create_user(username="fa1", password="pw")
    member = User.objects.create_user(username="fa2", password="pw")
    room = Room.objects.create(kind="group", title="G")
    RoomMembership.objects.create(room=room, user=owner, role="owner")
    RoomMembership.objects.create(room=room, user=member, role="member")

    c = Client()
    assert c.login(username="fa1", password="pw")
    # Build a tiny PNG file in memory
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
    f = SimpleUploadedFile("test.png", png_bytes, content_type="image/png")
    r = c.post(f"/messaging/rooms/{room.id}/messages/", {"message": "file", "file": f})
    assert r.status_code == 200

    r2 = c.get(f"/messaging/rooms/{room.id}/messages/?limit=1")
    assert r2.status_code == 200
    data = r2.json()
    results = data.get("results") or []
    assert results, data
    atts = results[-1].get("attachments") or []
    assert len(atts) == 1
    assert atts[0]["url"].startswith("/media/")
