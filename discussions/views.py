from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from accounts.decorators import role_required
from courses.models import Course, Enrolment
from .models import Question, Reply, Vote
from activity.models import Notification


def _can_participate(user, course: Course) -> bool:
    if not user.is_authenticated:
        return False
    if course.owner_id == user.id:
        return True
    return Enrolment.objects.filter(course=course, student=user).exists()


@login_required
def course_qna(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id)
    if not _can_participate(request.user, course):
        raise PermissionDenied

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "ask":
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            if not title:
                messages.error(request, "Title is required.")
            else:
                q = Question.objects.create(course=course, author=request.user, title=title, body=body)
                # notify owner
                Notification.objects.create(user=course.owner, actor=request.user, type=Notification.TYPE_QNA, course=course, message=f"New question: {title}")
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
                Reply.objects.create(question=q, author=request.user, body=body)
                # notify owner
                Notification.objects.create(user=course.owner, actor=request.user, type=Notification.TYPE_QNA, course=course, message=f"New reply on: {q.title}")
                messages.success(request, "Reply posted.")
            return redirect("discussions:course-qna", course_id=course.id)
        elif action == "upvote":
            try:
                qid = int(request.POST.get("question_id") or "0")
            except Exception:
                qid = 0
            q = get_object_or_404(Question, pk=qid, course=course)
            try:
                Vote.objects.get_or_create(question=q, user=request.user)
            except Exception:
                pass
            return redirect("discussions:course-qna", course_id=course.id)
        elif action == "pin":
            # Owner pin/unpin
            if course.owner_id != request.user.id:
                raise PermissionDenied
            try:
                qid = int(request.POST.get("question_id") or "0")
            except Exception:
                qid = 0
            q = get_object_or_404(Question, pk=qid, course=course)
            q.pinned = not q.pinned
            q.save(update_fields=["pinned"])
            return redirect("discussions:course-qna", course_id=course.id)

    # List questions with votes and replies
    qs = Question.objects.filter(course=course).prefetch_related("replies", "votes").all()
    # Map votes count
    items = []
    for q in qs:
        items.append({"q": q, "votes": q.votes.count(), "replies": list(q.replies.all())})
    return render(request, "discussions/course_qna.html", {"course": course, "items": items})

