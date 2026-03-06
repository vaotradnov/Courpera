from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    ChatMessage = apps.get_model("messaging", "ChatMessage")
    Room = apps.get_model("messaging", "Room")
    Message = apps.get_model("messaging", "Message")

    # Build or reuse course rooms and copy messages
    course_room_cache: dict[int, int] = {}
    for m in ChatMessage.objects.all().only(
        "id", "room", "course_id", "sender_id", "text", "created_at"
    ):
        course_id = m.course_id
        if course_id is None:
            # Skip non-course legacy messages (none expected)
            continue
        if course_id not in course_room_cache:
            room = Room.objects.create(kind="course", course_id=course_id, title="")
            course_room_cache[course_id] = room.id
        room_id = course_room_cache[course_id]
        Message.objects.create(
            room_id=room_id, sender_id=m.sender_id, text=m.text[:500], created_at=m.created_at
        )


def backwards(apps, schema_editor):
    # No safe reverse migration; keep as noop
    return


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0002_rooms_and_messages"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
