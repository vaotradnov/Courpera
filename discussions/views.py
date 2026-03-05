from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course

from .models import Question
from .services import (
    add_reply,
    can_participate,
    create_question,
    toggle_pin,
    upvote_question,
)


def _can_participate(user, course: Course) -> bool:
    # Backward-compatibility wrapper for tests; delegate to services
    return can_participate(user, course)


@login_required
def course_qna(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id)
    if not can_participate(request.user, course):
        raise PermissionDenied

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "ask":
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            if not title:
                messages.error(request, "Title is required.")
            else:
                create_question(course, request.user, title, body)
                messages.success(request, "Question posted.")
            return redirect("discussions:course-qna", course_id=course.id)
        elif action == "reply":
            try:
                qid = int(request.POST.get("question_id") or "0")
            except Exception:
                qid = 0
            q = get_object_or_404(Question, pk=qid, course=course)
            body = (request.POST.get("body") or "").strip()
            if not body:
                messages.error(request, "Reply cannot be empty.")
            else:
                add_reply(q, request.user, body)
                messages.success(request, "Reply posted.")
            return redirect("discussions:course-qna", course_id=course.id)
        elif action == "upvote":
            try:
                qid = int(request.POST.get("question_id") or "0")
            except Exception:
                qid = 0
            q = get_object_or_404(Question, pk=qid, course=course)
            upvote_question(q, request.user)
            return redirect("discussions:course-qna", course_id=course.id)
        elif action == "pin":
            # Owner pin/unpin
            try:
                qid = int(request.POST.get("question_id") or "0")
            except Exception:
                qid = 0
            q = get_object_or_404(Question, pk=qid, course=course)
            toggle_pin(q, request.user)
            return redirect("discussions:course-qna", course_id=course.id)

    # List questions with votes and replies
    qs = Question.objects.filter(course=course).prefetch_related("replies", "votes").all()
    # Map votes count
    items = []
    for q in qs:
        items.append({"q": q, "votes": q.votes.count(), "replies": list(q.replies.all())})
    return render(request, "discussions/course_qna.html", {"course": course, "items": items})
