from __future__ import annotations

from datetime import timedelta
from typing import cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from config.metrics import inc as metrics_inc
from courses.models import Course, Enrolment

from .models import (
    Attachment,
    Message,
    Reaction,
    Report,
    Room,
    RoomMembership,
    validate_chat_upload,
)
from .services import create_chat_notifications_for_message


@login_required
def rooms_mine(request: HttpRequest) -> JsonResponse:
    """Return conversations for the current user with last message and unread count.

    Includes DM/group memberships and course rooms for courses the user owns or is enrolled in.
    Ensures a membership exists for course rooms to track last_read_at.
    """
    user = cast(User, request.user)
    now = timezone.now()
    # Collect DM and group rooms via membership
    mem_qs = (
        RoomMembership.objects.select_related("room", "room__course")
        .filter(user_id=user.id)
        .order_by("-created_at")
    )
    rooms = {m.room_id: m for m in mem_qs}
    # Include course rooms where user is owner or enrolled
    course_ids = set(Course.objects.filter(owner_id=user.id).values_list("id", flat=True))
    enrolled_ids = set(
        Enrolment.objects.filter(student_id=user.id).values_list("course_id", flat=True)
    )
    for cid in sorted(course_ids | enrolled_ids):
        room = Room.objects.filter(kind=Room.KIND_COURSE, course_id=cid).first()
        if room is None:
            room = Room.objects.create(kind=Room.KIND_COURSE, course_id=cid, title="")
        mem = rooms.get(room.id)
        if mem is None:
            role = RoomMembership.ROLE_OWNER if cid in course_ids else RoomMembership.ROLE_MEMBER
            mem, _ = RoomMembership.objects.get_or_create(
                room=room, user=user, defaults={"role": role}
            )
            rooms[room.id] = mem
    # Build response
    out = []
    for rid, mem in rooms.items():
        r = mem.room
        # Title logic
        if r.kind == Room.KIND_DM:
            # Show the other user's username
            others = (
                RoomMembership.objects.filter(room_id=r.id)
                .exclude(user_id=user.id)
                .select_related("user")
            )
            title = getattr(next(iter(others), None), "user", None)
            title = getattr(title, "username", "Direct message")
        elif r.kind == Room.KIND_GROUP:
            title = r.title or "Group"
        else:
            title = getattr(r.course, "title", None) or "Course chat"
        last = (
            Message.objects.filter(room_id=r.id, visible_at__lte=now)
            .select_related("sender")
            .order_by("-created_at", "-id")
            .first()
        )
        last_obj = (
            {
                "text": last.text,
                "created_at": last.created_at.isoformat(),
                "sender": getattr(last.sender, "username", ""),
            }
            if last
            else None
        )
        # Unread: created_at > last_read_at and not sent by me
        lr = mem.last_read_at
        unread_qs = Message.objects.filter(room_id=r.id, visible_at__lte=now).exclude(
            sender_id=user.id
        )
        if lr is not None:
            unread_qs = unread_qs.filter(created_at__gt=lr)
        unread = unread_qs.count()
        out.append(
            {
                "id": r.id,
                "kind": r.kind,
                "title": title,
                "unread": unread,
                "last_message": last_obj,
            }
        )

    # Sort by last_message created_at desc (None last)
    def _key(it):
        lm = it.get("last_message") or {}
        return lm.get("created_at") or ""

    out.sort(key=_key, reverse=True)
    return JsonResponse({"results": out})


@login_required
def room_read(request: HttpRequest, room_id: int) -> JsonResponse:
    """Mark a conversation as read for the current user."""
    if request.method not in {"POST", "PATCH"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    user = cast(User, request.user)
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    # Ensure access/membership
    mem = RoomMembership.objects.filter(room=room, user_id=user.id).first()
    if room.kind == Room.KIND_COURSE:
        if not mem:
            # Permit owner/enrolled and create membership for tracking
            course = room.course
            if not course:
                return JsonResponse({"detail": "Not permitted"}, status=403)
            if not (
                course.owner_id == user.id
                or Enrolment.objects.filter(course=course, student_id=user.id).exists()
            ):
                return JsonResponse({"detail": "Not permitted"}, status=403)
            role = (
                RoomMembership.ROLE_OWNER
                if course.owner_id == user.id
                else RoomMembership.ROLE_MEMBER
            )
            mem = RoomMembership.objects.create(room=room, user=user, role=role)
    else:
        if not mem:
            return JsonResponse({"detail": "Not permitted"}, status=403)
    mem.last_read_at = timezone.now()
    mem.save(update_fields=["last_read_at"])
    return JsonResponse({"unread": 0, "last_read_at": mem.last_read_at.isoformat()})


@login_required
def room_members(request: HttpRequest, room_id: int) -> JsonResponse:
    """Return members of a room (id, username)."""
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    user = cast(User, request.user)
    # Access: member; or course owner/enrolled for course rooms
    mem = RoomMembership.objects.filter(room=room, user_id=user.id).first()
    if room.kind == Room.KIND_COURSE and not mem:
        course = room.course
        if not course or not (
            course.owner_id == user.id
            or Enrolment.objects.filter(course=course, student_id=user.id).exists()
        ):
            return JsonResponse({"detail": "Not permitted"}, status=403)
    elif not mem:
        return JsonResponse({"detail": "Not permitted"}, status=403)
    members = RoomMembership.objects.filter(room=room).select_related("user").order_by("created_at")
    out = [{"id": m.user_id, "username": getattr(m.user, "username", "")} for m in members]
    self_lr = None
    try:
        self_lr = (
            RoomMembership.objects.filter(room=room, user_id=user.id)
            .values_list("last_read_at", flat=True)
            .first()
        )
    except Exception:
        self_lr = None
    return JsonResponse(
        {
            "results": out,
            "kind": room.kind,
            "title": room.title or "",
            "self_last_read_at": self_lr.isoformat() if self_lr else None,
        }
    )


def _can_manage_room(user: User, room: Room) -> bool:
    if room.kind == Room.KIND_COURSE:
        return bool(room.course and room.course.owner_id == user.id)
    # DM/Group: any member
    return RoomMembership.objects.filter(room=room, user_id=user.id).exists()


@login_required
def room_rename(request: HttpRequest, room_id: int) -> JsonResponse:
    if request.method not in {"POST", "PATCH"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    user = cast(User, request.user)
    if not _can_manage_room(user, room):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    if room.kind == Room.KIND_DM:
        return JsonResponse({"detail": "Rename not supported for DMs"}, status=400)
    title = (request.POST.get("title") or request.GET.get("title") or "").strip()
    if not title:
        return JsonResponse({"detail": "Title required"}, status=400)
    room.title = title
    room.save(update_fields=["title"])
    return JsonResponse({"title": room.title})


@login_required
def room_members_add(request: HttpRequest, room_id: int) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    user = cast(User, request.user)
    if not _can_manage_room(user, room):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    q = (
        request.POST.get("q")
        or request.POST.get("username")
        or request.POST.get("email")
        or request.POST.get("user_id")
        or ""
    ).strip()
    target: User | None = None
    if q.isdigit():
        target = User.objects.filter(pk=int(q)).first()
    elif "@" in q:
        target = User.objects.filter(email__iexact=q).first()
    else:
        target = User.objects.filter(username=q).first()
    if not target:
        return JsonResponse({"detail": "User not found"}, status=404)
    if RoomMembership.objects.filter(room=room, user=target).exists():
        return JsonResponse({"added": False, "detail": "Already a member"})
    # If DM and adding a third person, convert to group
    if room.kind == Room.KIND_DM:
        room.kind = Room.KIND_GROUP
        if not room.title:
            room.title = "Group"
        room.save(update_fields=["kind", "title"])
    RoomMembership.objects.create(room=room, user=target, role=RoomMembership.ROLE_MEMBER)
    return JsonResponse({"added": True})


@login_required
def room_members_remove(request: HttpRequest, room_id: int) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    room = get_object_or_404(Room.objects.select_related("course"), pk=room_id)
    user = cast(User, request.user)
    if not _can_manage_room(user, room):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    uid_s = (request.POST.get("user_id") or "").strip()
    if not uid_s.isdigit():
        return JsonResponse({"detail": "user_id required"}, status=400)
    uid = int(uid_s)
    if uid == user.id:
        return JsonResponse({"detail": "Use leave endpoint to remove yourself"}, status=400)
    if room.kind == Room.KIND_COURSE:
        return JsonResponse({"detail": "Cannot remove from course chat"}, status=400)
    RoomMembership.objects.filter(room=room, user_id=uid).delete()
    return JsonResponse({"removed": True})


@login_required
def room_leave(request: HttpRequest, room_id: int) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    room = get_object_or_404(Room, pk=room_id)
    user = cast(User, request.user)
    if room.kind == Room.KIND_COURSE:
        return JsonResponse({"detail": "Cannot leave course chat"}, status=400)
    RoomMembership.objects.filter(room=room, user_id=user.id).delete()
    return JsonResponse({"left": True})


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
    items = (
        Message.objects.filter(room=room, visible_at__lte=timezone.now())
        .select_related("sender")
        .order_by("-created_at", "-id")[:50]
    )
    # Return oldest first for readability; include ids and attachments for UI parity
    data = []
    for m in reversed(list(items)):
        data.append(
            {
                "id": m.id,
                "sender": m.sender.username,
                "message": m.text,
                "created_at": m.created_at.isoformat(),
                "parent_id": m.parent_message_id,
                "attachments": [
                    {"id": a.id, "url": a.file.url, "mime": a.mime, "size": a.size_bytes}
                    for a in m.attachments.all()
                ],
            }
        )
    return JsonResponse(
        {
            "results": data,
            "room_id": room.id,
            "slow_mode_seconds": room.slow_mode_seconds,
            "slow_mode_expires_at": room.slow_mode_expires_at.isoformat()
            if room.slow_mode_expires_at
            else None,
        }
    )


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
        # Enforce slow mode (applies to all members, including course rooms)
        # Compute effective slow mode (auto-clear if expired)
        ssecs = int(room.slow_mode_seconds or 0)
        if ssecs and room.slow_mode_expires_at and timezone.now() >= room.slow_mode_expires_at:
            room.slow_mode_seconds = 0
            room.slow_mode_expires_at = None
            room.save(update_fields=["slow_mode_seconds", "slow_mode_expires_at"])
            ssecs = 0
        if ssecs:
            last = (
                Message.objects.filter(room=room, sender=user)
                .order_by("-created_at", "-id")
                .only("created_at")
                .first()
            )
            if last is not None:
                delta = (timezone.now() - last.created_at).total_seconds()
                if delta < float(ssecs):
                    return JsonResponse({"detail": "Slow mode active"}, status=429)

        # Collect and validate attachments first; fail early on error
        files: list[UploadedFile] = []
        if request.FILES:
            if getattr(request.FILES, "getlist", None) and request.FILES.getlist("files"):
                files = cast(list[UploadedFile], request.FILES.getlist("files"))
            elif request.FILES.get("file"):
                single = cast(UploadedFile, request.FILES["file"])
                files = [single]
        if len(files) > 3:
            files = files[:3]
        for f in files:
            try:
                validate_chat_upload(f)
            except Exception as e:
                return JsonResponse({"detail": str(e) or "Invalid attachment"}, status=400)

        # Per-member moderation: ban/mute/delay
        mem = RoomMembership.objects.filter(room=room, user_id=user.id).first()
        if mem and getattr(mem, "banned", False):
            return JsonResponse({"detail": "You are banned in this room"}, status=403)
        if mem and getattr(mem, "muted_until", None):
            mu = mem.muted_until
            if mu and mu > timezone.now():
                return JsonResponse({"detail": "You are muted"}, status=403)

        delay_secs = int(getattr(mem, "delay_seconds", 0) or 0) if mem else 0
        if delay_secs > 0:
            m = Message.objects.create(
                room=room,
                sender=user,
                text=txt,
                parent_message=parent,
                visible_at=timezone.now() + timedelta(seconds=delay_secs),
            )
            try:
                metrics_inc("courpera_messages_created_total", 1)
            except Exception:
                pass
            for f in files:
                Attachment.objects.create(message=m, file=f)
            return JsonResponse(
                {"id": m.id, "queued": True, "visible_at": m.visible_at.isoformat()}
            )
        else:
            m = Message.objects.create(room=room, sender=user, text=txt, parent_message=parent)
            try:
                metrics_inc("courpera_messages_created_total", 1)
            except Exception:
                pass
            for f in files:
                Attachment.objects.create(message=m, file=f)

            # Mark as published and broadcast immediate
            m.published_at = timezone.now()
            m.save(update_fields=["published_at"])
            # Create in-app notifications (best-effort; ignore errors)
            try:
                create_chat_notifications_for_message(m)
            except Exception:
                pass
            layer = get_channel_layer()
            atts = [
                {"id": a.id, "url": a.file.url, "mime": a.mime, "size": a.size_bytes}
                for a in m.attachments.all()
            ]
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
                        "attachments": atts,
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
    qs = (
        Message.objects.filter(room=room, visible_at__lte=timezone.now())
        .select_related("sender")
        .order_by("-created_at", "-id")
    )
    if before:
        from django.utils.dateparse import parse_datetime

        dt = parse_datetime(before)
        if dt is not None:
            qs = qs.filter(created_at__lt=dt)
    items = list(qs[:limit])
    data = []
    for m in reversed(items):
        data.append(
            {
                "id": m.id,
                "sender": m.sender.username,
                "message": m.text,
                "created_at": m.created_at.isoformat(),
                "parent_id": m.parent_message_id,
                "attachments": [
                    {
                        "id": a.id,
                        "url": a.file.url,
                        "mime": a.mime,
                        "size": a.size_bytes,
                    }
                    for a in m.attachments.all()
                ],
            }
        )
    next_before = data[0]["created_at"] if data else None
    return JsonResponse({"results": data, "next_before": next_before})


@login_required
def create_dm(request: HttpRequest) -> JsonResponse:
    """Create or return a DM room between the current user and another user.

    Accepts one of: user_id, username, email, or q (auto-detected: digits=id, contains '@'=email, else username).
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    other_id = (request.POST.get("user_id") or "").strip()
    other_username = (request.POST.get("username") or "").strip()
    other_email = (request.POST.get("email") or "").strip()
    q = (request.POST.get("q") or "").strip()
    if q and not (other_id or other_username or other_email):
        if q.isdigit():
            other_id = q
        elif "@" in q:
            other_email = q
        else:
            other_username = q
    other: User | None = None
    if other_id.isdigit():
        other = User.objects.filter(pk=int(other_id)).first()
    if not other and other_email:
        other = User.objects.filter(email__iexact=other_email).first()
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
    """Create a group chat room. Creator becomes owner. Members optional.

    Accepts:
    - member_ids: comma-separated user IDs (legacy)
    - members: comma/space-separated tokens (id, email, or username)
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"detail": "Title required"}, status=400)
    user = cast(User, request.user)
    room = Room.objects.create(kind=Room.KIND_GROUP, title=title)
    RoomMembership.objects.create(room=room, user=user, role=RoomMembership.ROLE_OWNER)
    # Gather members
    tokens: list[str] = []
    legacy = (request.POST.get("member_ids") or "").strip()
    if legacy:
        tokens.extend([p.strip() for p in legacy.split(",") if p.strip()])
    members = (request.POST.get("members") or "").strip()
    if members:
        for part in members.replace("\n", ",").replace(" ", ",").split(","):
            if part.strip():
                tokens.append(part.strip())
    added = set()
    for tok in tokens:
        u: User | None = None
        if tok.isdigit():
            u = User.objects.filter(pk=int(tok)).first()
        elif "@" in tok:
            u = User.objects.filter(email__iexact=tok).first()
        else:
            u = User.objects.filter(username=tok).first()
        if not u or u.id == user.id or u.id in added:
            continue
        RoomMembership.objects.get_or_create(
            room=room, user=u, defaults={"role": RoomMembership.ROLE_MEMBER}
        )
        added.add(u.id)
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


@login_required
def report_message(request: HttpRequest, message_id: int) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    msg = get_object_or_404(Message, pk=message_id)
    reason = (request.POST.get("reason") or "").strip() or "inappropriate"
    Report.objects.create(message=msg, reporter=cast(User, request.user), reason=reason)
    return JsonResponse({"reported": True})


@login_required
def moderate_member(request: HttpRequest, room_id: int, user_id: int, action: str) -> JsonResponse:
    room = get_object_or_404(Room, pk=room_id)
    me = cast(User, request.user)
    is_owner_member = RoomMembership.objects.filter(
        room=room, user_id=me.id, role=RoomMembership.ROLE_OWNER
    ).exists()
    is_course_owner = bool(room.course and room.course.owner_id == me.id)
    if not (is_owner_member or is_course_owner):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    # Create a membership record for the target if missing (especially for course rooms)
    mem, _ = RoomMembership.objects.get_or_create(
        room=room, user_id=user_id, defaults={"role": RoomMembership.ROLE_MEMBER}
    )
    if action == "mute":
        minutes = int(request.GET.get("minutes") or "5")
        mem.muted_until = timezone.now() + timedelta(minutes=minutes)
        mem.save(update_fields=["muted_until"])
        # Notify room (targeted user will filter on client)
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "moderation.state",
                    "action": "mute",
                    "target_id": mem.user_id,
                    "until": mem.muted_until.isoformat() if mem.muted_until else None,
                },
            },
        )
        return JsonResponse(
            {"muted": True, "until": mem.muted_until.isoformat() if mem.muted_until else None}
        )
    if action == "unmute":
        mem.muted_until = None
        mem.save(update_fields=["muted_until"])
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "moderation.state",
                    "action": "unmute",
                    "target_id": mem.user_id,
                },
            },
        )
        return JsonResponse({"muted": False})
    if action == "ban":
        mem.banned = True
        mem.save(update_fields=["banned"])
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "moderation.state",
                    "action": "ban",
                    "target_id": mem.user_id,
                },
            },
        )
        return JsonResponse({"banned": True})
    if action == "unban":
        mem.banned = False
        mem.save(update_fields=["banned"])
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "moderation.state",
                    "action": "unban",
                    "target_id": mem.user_id,
                },
            },
        )
        return JsonResponse({"banned": False})
    if action == "delay":
        try:
            secs = int(request.GET.get("seconds") or request.POST.get("seconds") or "0")
        except Exception:
            secs = 0
        secs = max(0, min(3600, secs))
        mem.delay_seconds = secs
        mem.save(update_fields=["delay_seconds"])
        return JsonResponse({"delay_seconds": mem.delay_seconds})
    if action == "cleardelay":
        mem.delay_seconds = 0
        mem.save(update_fields=["delay_seconds"])
        return JsonResponse({"delay_seconds": 0})
    return JsonResponse({"detail": "Unknown action"}, status=400)


@login_required
def slowmode(request: HttpRequest, room_id: int) -> JsonResponse:
    room = get_object_or_404(Room, pk=room_id)
    me = cast(User, request.user)
    # Authorize: room owner (membership) or course owner for course rooms
    is_owner_member = RoomMembership.objects.filter(
        room=room, user_id=me.id, role=RoomMembership.ROLE_OWNER
    ).exists()
    if room.kind == Room.KIND_COURSE:
        course_owner_ok = bool(room.course and room.course.owner_id == me.id)
    else:
        course_owner_ok = False
    if not (is_owner_member or course_owner_ok):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    if request.method not in {"PATCH", "POST"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        seconds = int(
            request.POST.get("slow_mode_seconds") or request.GET.get("slow_mode_seconds") or "0"
        )
    except Exception:
        seconds = 0
    seconds = max(0, min(60, seconds))
    room.slow_mode_seconds = seconds
    room.slow_mode_expires_at = timezone.now() + timedelta(seconds=seconds) if seconds > 0 else None
    room.save(update_fields=["slow_mode_seconds", "slow_mode_expires_at"])
    # Broadcast activation notice to all participants
    if seconds > 0:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "system.notice",
                    "message": f"Slow mode activated for {seconds} seconds",
                    "expires_at": room.slow_mode_expires_at.isoformat()
                    if room.slow_mode_expires_at
                    else None,
                },
            },
        )
    else:
        # Broadcast turn-off so all clients can clear their countdowns immediately
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"room_{room.id}",
            {
                "type": "chat_message",
                "payload": {
                    "type": "system.notice",
                    "message": "Slow mode turned off",
                    "expires_at": None,
                },
            },
        )
    return JsonResponse(
        {
            "slow_mode_seconds": room.slow_mode_seconds,
            "slow_mode_expires_at": room.slow_mode_expires_at.isoformat()
            if room.slow_mode_expires_at
            else None,
        }
    )
