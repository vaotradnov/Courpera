from __future__ import annotations

from typing import cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404

from courses.models import Course, Enrolment

from .models import Message, Room, RoomMembership


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
    """Paginated history for a room. Requires membership or course enrolment."""
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
