from __future__ import annotations

from typing import cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from courses.models import Course, Enrolment

from .models import Message, Reaction, Room, RoomMembership


def _is_owner(user: User, course: Course) -> bool:
    return bool(user and user.is_authenticated and course.owner_id == user.id)


def _is_enrolled(user: User, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return Enrolment.objects.filter(course=course, student_id=user.id).exists()


@login_required
def course_history(request: HttpRequest, course_id: int) -> JsonResponse:
    """Return recent chat messages for a course (owner or enrolled only)."""
    course = get_object_or_404(Course, pk=course_id)
    user = cast(User, request.user)
    if not (_is_owner(user, course) or _is_enrolled(user, course)):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    # Resolve or create the backing Room(kind=course)
    room = Room.objects.filter(kind=Room.KIND_COURSE, course=course).first()
    if not room:
        room = Room.objects.create(kind=Room.KIND_COURSE, course=course, title="")
    items = Message.objects.filter(room=room).select_related("sender").order_by("-created_at")[:50]
    # Return oldest first for readability
    data = [
        {
            "sender": m.sender.username,
            "message": m.text,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(list(items))
    ]
    return JsonResponse({"results": data})


@login_required
def room_messages(request: HttpRequest, room_id: int) -> JsonResponse:
    """GET: paginated history; POST: create message (optional parent_id)."""
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    # Auth
    if room.kind == Room.KIND_COURSE:
        course = room.course
        user = cast(User, request.user)
        if not course or not (_is_owner(user, course) or _is_enrolled(user, course)):
            return JsonResponse({"detail": "Not permitted"}, status=403)
    else:
        user = cast(User, request.user)
        if not RoomMembership.objects.filter(room=room, user_id=user.id).exists():
            return JsonResponse({"detail": "Not permitted"}, status=403)

    if request.method == "POST":
        # Create a new message
        txt = (request.POST.get("message") or "").strip()
        if not txt:
            return JsonResponse({"detail": "Message required"}, status=400)
        parent_id = request.POST.get("parent_id")
        parent = None
        if parent_id and parent_id.isdigit():
            parent = Message.objects.filter(room=room, pk=int(parent_id)).first()
        if len(txt) > 500:
            txt = txt[:500]
        m = Message.objects.create(room=room, sender=user, text=txt, parent_message=parent)
        # Broadcast
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "message.new",
                    "id": m.id,
                    "sender": user.username,
                    "message": m.text,
                    "created_at": m.created_at.isoformat(),
                    "parent_id": m.parent_message_id,
                },
            },
        )
        return JsonResponse({"id": m.id})

    # Pagination: before=iso timestamp, limit=1..100
    before = request.GET.get("before")
    limit_s = request.GET.get("limit") or "50"
    try:
        limit = max(1, min(100, int(limit_s)))
    except Exception:
        limit = 50
    qs = Message.objects.filter(room=room).select_related("sender").order_by("-created_at", "-id")
    if before:
        from django.utils.dateparse import parse_datetime

        dt = parse_datetime(before)
        if dt is not None:
            qs = qs.filter(created_at__lt=dt)
    items = list(qs[:limit])
    data = [
        {"sender": m.sender.username, "message": m.text, "created_at": m.created_at.isoformat()}
        for m in reversed(items)
    ]
    next_before = data[0]["created_at"] if data else None
    return JsonResponse({"results": data, "next_before": next_before})


@login_required
def create_dm(request: HttpRequest) -> JsonResponse:
    """Create or return a DM room between the current user and another user."""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    other_id = request.POST.get("user_id") or ""
    other_username = request.POST.get("username") or ""
    other: User | None = None
    if other_id.isdigit():
        other = User.objects.filter(pk=int(other_id)).first()
    if not other and other_username:
        other = User.objects.filter(username=other_username).first()
    if not other:
        return JsonResponse({"detail": "User not found"}, status=404)
    me = cast(User, request.user)
    if other.id == me.id:
        return JsonResponse({"detail": "Cannot DM yourself"}, status=400)

    # Find existing DM room with exactly these two users
    # Find any DM room that already has both users as members
    candidate = (
        Room.objects.filter(kind=Room.KIND_DM, memberships__user_id=me.id)
        .filter(memberships__user_id=other.id)
        .distinct()
        .first()
    )
    if candidate is None:
        candidate = Room.objects.create(kind=Room.KIND_DM, title="")
        RoomMembership.objects.bulk_create(
            [
                RoomMembership(room=candidate, user=me, role=RoomMembership.ROLE_OWNER),
                RoomMembership(room=candidate, user=other, role=RoomMembership.ROLE_MEMBER),
            ]
        )
    return JsonResponse({"room_id": candidate.id})


@login_required
def create_group(request: HttpRequest) -> JsonResponse:
    """Create a group chat room. Creator becomes owner. Optional member_ids."""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"detail": "Title required"}, status=400)
    user = cast(User, request.user)
    room = Room.objects.create(kind=Room.KIND_GROUP, title=title)
    RoomMembership.objects.create(room=room, user=user, role=RoomMembership.ROLE_OWNER)
    # Optional: member_ids as comma-separated
    raw = request.POST.get("member_ids") or ""
    ids = []
    for part in raw.split(","):
        p = part.strip()
        if p.isdigit():
            ids.append(int(p))
    for uid in ids:
        if uid == user.id:
            continue
        u = User.objects.filter(pk=uid).first()
        if u:
            RoomMembership.objects.get_or_create(
                room=room, user=u, defaults={"role": RoomMembership.ROLE_MEMBER}
            )
    return JsonResponse({"room_id": room.id})


@login_required
def edit_message(request: HttpRequest, message_id: int) -> JsonResponse:
    """Edit a message (sender within 15 min or room owner)."""
    if request.method not in {"PATCH", "POST"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    msg = get_object_or_404(Message.objects.select_related("room", "sender"), pk=message_id)
    user = cast(User, request.user)
    room = msg.room
    is_owner = RoomMembership.objects.filter(
        room=room, user_id=user.id, role=RoomMembership.ROLE_OWNER
    ).exists()
    window_ok = (timezone.now() - msg.created_at).total_seconds() <= 15 * 60
    if not (user.id == msg.sender_id and window_ok) and not is_owner:
        return JsonResponse({"detail": "Not permitted"}, status=403)
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"detail": "Message required"}, status=400)
    if len(text) > 500:
        text = text[:500]
    msg.text = text
    msg.edited_at = timezone.now()
    msg.save(update_fields=["text", "edited_at"])
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        f"room_{room.id}",
        {
            "type": "chat_message",
            "payload": {
                "type": "message.update",
                "id": msg.id,
                "message": msg.text,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            },
        },
    )
    return JsonResponse({"id": msg.id, "edited_at": msg.edited_at.isoformat()})


@login_required
def delete_message(request: HttpRequest, message_id: int) -> JsonResponse:
    """Soft-delete a message (sender within 15 min or room owner)."""
    if request.method not in {"DELETE", "POST"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    msg = get_object_or_404(Message.objects.select_related("room", "sender"), pk=message_id)
    user = cast(User, request.user)
    room = msg.room
    is_owner = RoomMembership.objects.filter(
        room=room, user_id=user.id, role=RoomMembership.ROLE_OWNER
    ).exists()
    window_ok = (timezone.now() - msg.created_at).total_seconds() <= 15 * 60
    if not (user.id == msg.sender_id and window_ok) and not is_owner:
        return JsonResponse({"detail": "Not permitted"}, status=403)
    msg.deleted_at = timezone.now()
    msg.deleted_by = user
    msg.save(update_fields=["deleted_at", "deleted_by"])
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        f"room_{room.id}",
        {
            "type": "chat_message",
            "payload": {
                "type": "message.delete",
                "id": msg.id,
                "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
            },
        },
    )
    return JsonResponse({"id": msg.id, "deleted": True})


@login_required
def toggle_reaction(request: HttpRequest, message_id: int) -> JsonResponse:
    """POST add a reaction; DELETE remove."""
    msg = get_object_or_404(Message.objects.select_related("room"), pk=message_id)
    user = cast(User, request.user)
    emoji = (request.POST.get("emoji") or request.GET.get("emoji") or "").strip()
    if not emoji:
        return JsonResponse({"detail": "Emoji required"}, status=400)
    # Auth: member or course owner/enrolled
    if msg.room.kind == Room.KIND_COURSE:
        course = msg.room.course
        if not course or not (_is_owner(user, course) or _is_enrolled(user, course)):
            return JsonResponse({"detail": "Not permitted"}, status=403)
    else:
        if not RoomMembership.objects.filter(room=msg.room, user_id=user.id).exists():
            return JsonResponse({"detail": "Not permitted"}, status=403)
    layer = get_channel_layer()
    if request.method == "DELETE":
        Reaction.objects.filter(message=msg, user=user, emoji=emoji).delete()
        async_to_sync(layer.group_send)(
            f"room_{msg.room_id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "reaction.remove",
                    "message_id": msg.id,
                    "emoji": emoji,
                    "user": user.username,
                },
            },
        )
        return JsonResponse({"removed": True})
    Reaction.objects.get_or_create(message=msg, user=user, emoji=emoji)
    async_to_sync(layer.group_send)(
        f"room_{msg.room_id}",
        {
            "type": "chat_message",
            "payload": {
                "type": "reaction.add",
                "message_id": msg.id,
                "emoji": emoji,
                "user": user.username,
            },
        },
    )
    return JsonResponse({"added": True})
