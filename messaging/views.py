from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404

from courses.models import Course, Enrolment

from .models import ChatMessage


def _is_owner(user, course: Course) -> bool:
    return bool(user and user.is_authenticated and course.owner_id == user.id)


def _is_enrolled(user, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return Enrolment.objects.filter(course=course, student=user).exists()


@login_required
def course_history(request: HttpRequest, course_id: int) -> JsonResponse:
    """Return recent chat messages for a course (owner or enrolled only)."""
    course = get_object_or_404(Course, pk=course_id)
    if not (_is_owner(request.user, course) or _is_enrolled(request.user, course)):
        return JsonResponse({"detail": "Not permitted"}, status=403)
    room = f"course_{course_id}"
    items = (
        ChatMessage.objects.filter(room=room).select_related("sender").order_by("-created_at")[:50]
    )
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
