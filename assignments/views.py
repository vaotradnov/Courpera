from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone 
from datetime import timedelta
from django.conf import settings

from accounts.models import Role
from accounts.decorators import role_required
from courses.models import Course, Enrolment

from django.db import models 
from .models import (
    Assignment,
    AssignmentType,
    QuizQuestion,
    QuizAnswerChoice,
    Attempt,
    StudentAnswer,
)
from .forms import AssignmentForm, QuizQuestionForm, QuizAnswerChoiceForm, AssignmentMetaForm, GradeAttemptForm 
from .utils import grade_quiz, quiz_readiness, upsert_grade_for_attempt, recalc_grades_for_assignment
from activity.models import Notification


def _is_teacher_owner(user, course: Course) -> bool:
    return bool(user.is_authenticated and getattr(getattr(user, "profile", None), "role", None) == Role.TEACHER and course.owner_id == user.id)


def _is_enrolled(user, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return Enrolment.objects.filter(course=course, student=user).exists()


@login_required
def course_assignments(request, course_id: int): 
    course = get_object_or_404(Course, pk=course_id)
    owner = _is_teacher_owner(request.user, course)
    if not (owner or _is_enrolled(request.user, course)):
        raise PermissionDenied
    assignments = Assignment.objects.filter(course=course).prefetch_related("questions__choices").order_by("title") 
    now = timezone.now()
    for a in assignments: 
        if a.type == AssignmentType.QUIZ: 
            setattr(a, "ready_info", quiz_readiness(a)) 
        else: 
            setattr(a, "ready_info", None) 
        setattr(a, "avail_ok", (a.available_from is None) or (now >= a.available_from))
    # For students, compute attempts used/left per assignment
    if not owner:
        ids = [a.id for a in assignments]
        used_qs = (
            Attempt.objects.filter(assignment_id__in=ids, student=request.user)
            .values("assignment_id")
            .annotate(c=models.Count("id"))
        )
        used_map = {row["assignment_id"]: row["c"] for row in used_qs}
        for a in assignments:
            used = used_map.get(a.id, 0)
            setattr(a, "attempts_used", used)
            setattr(a, "attempts_left", max(0, (a.attempts_allowed or 0) - used))
    return render(request, "assignments/course_assignments.html", {"course": course, "assignments": assignments, "owner_view": owner})


@login_required
@role_required(Role.TEACHER)
def assignment_create(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id)
    if not _is_teacher_owner(request.user, course):
        raise PermissionDenied
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        # Support quick actions without triggering HTML5 validation
        if action == "set_available_now":
            data = request.POST.copy()
            data["available_from"] = timezone.localtime(timezone.now(), timezone.get_current_timezone()).strftime("%Y-%m-%dT%H:%M")
            form = AssignmentForm(data)
            return render(request, "assignments/assignment_create.html", {"form": form, "course": course})
        if action == "set_deadline_delta":
            delta_str = (request.POST.get("deadline_delta") or "").strip()
            mapping = {
                "1d": timedelta(days=1),
                "3d": timedelta(days=3),
                "1w": timedelta(weeks=1),
                "2w": timedelta(weeks=2),
                "1m": timedelta(days=30),
                "3m": timedelta(days=90),
            }
            td = mapping.get(delta_str)
            data = request.POST.copy()
            try:
                base_str = data.get("available_from") or ""
                base = None
                if base_str:
                    # Parse naive local from widget and make aware
                    from datetime import datetime as _dt
                    base_naive = _dt.strptime(base_str, "%Y-%m-%dT%H:%M")
                    base = timezone.make_aware(base_naive, timezone.get_current_timezone())
            except Exception:
                base = None
            base = base or timezone.localtime(timezone.now(), timezone.get_current_timezone())
            if td is not None:
                data["deadline"] = (base + td).strftime("%Y-%m-%dT%H:%M")
            form = AssignmentForm(data)
            return render(request, "assignments/assignment_create.html", {"form": form, "course": course})
        # Normal create
        form = AssignmentForm(request.POST)
        if form.is_valid():
            a = form.save(commit=False)
            a.course = course
            a.save()
            messages.success(request, "Assignment created.") 
            if a.type == AssignmentType.QUIZ: 
                return redirect("assignments:quiz-manage", pk=a.pk) 
            # For Paper/Exam, go directly to generic manage page for meta edits
            return redirect("assignments:manage", pk=a.pk) 
    else:
        form = AssignmentForm()
    return render(request, "assignments/assignment_create.html", {"form": form, "course": course})


@login_required
@role_required(Role.TEACHER)
def assignment_delete(request, pk: int):
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    if not _is_teacher_owner(request.user, a.course):
        raise PermissionDenied
    if request.method != "POST":
        messages.error(request, "Please confirm deletion via the form.")
        return redirect("assignments:course", course_id=a.course_id)
    if Attempt.objects.filter(assignment=a).exists():
        messages.error(request, "Cannot delete: attempts exist.")
        return redirect("assignments:course", course_id=a.course_id)
    a.delete()
    messages.success(request, "Assignment deleted.")
    return redirect("assignments:course", course_id=a.course_id)


@login_required
@role_required(Role.TEACHER)
def quiz_manage(request, pk: int): 
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    if a.type != AssignmentType.QUIZ:
        messages.error(request, "Not a quiz assignment.")
        return redirect("assignments:course", course_id=a.course_id)
    if not _is_teacher_owner(request.user, a.course):
        raise PermissionDenied
    # Lock structural editing once attempts exist; compute readiness banner
    locked = Attempt.objects.filter(assignment=a).exists()
    attempts_count = Attempt.objects.filter(assignment=a).count()
    ready_info = quiz_readiness(a) if a.type == AssignmentType.QUIZ else {"ready": True, "issues": []}
    q_form = QuizQuestionForm()
    c_form = QuizAnswerChoiceForm()
    meta_form = AssignmentMetaForm(instance=a) 
    # Session toggle for add-choice mark-correct state
    toggle_key = f"quiz_add_correct_{a.id}"
    add_mark_correct = bool(request.session.get(toggle_key, False))

    # Inline choice edit mode (GET): use ?edit_choice=<id>
    try:
        edit_choice_id = int(request.GET.get("edit_choice")) if request.GET.get("edit_choice") else None
    except Exception:
        edit_choice_id = None

    # Build questions list with counts for template badges
    try:
        questions = list(a.questions.order_by("order").prefetch_related("choices"))
        for q in questions:
            chs = list(q.choices.all())
            setattr(q, "choice_count", len(chs))
            setattr(q, "correct_count", sum(1 for c in chs if getattr(c, "is_correct", False)))
    except Exception:
        questions = list(a.questions.order_by("order").all())
        for q in questions:
            setattr(q, "choice_count", q.choices.count())
            setattr(q, "correct_count", q.choices.filter(is_correct=True).count())

    if request.method == "POST": 
        action = request.POST.get("action", "") 
        # Meta updates allowed even if locked 
        if action == "update_meta":
            # Apply attempts update defensively even if other fields are invalid
            old_policy = a.attempts_policy
            try:
                new_attempts = int((request.POST.get("attempts_allowed") or "").strip() or 0)
                if new_attempts >= 1:
                    used = Attempt.objects.filter(assignment=a).count()
                    if new_attempts >= used and new_attempts != a.attempts_allowed:
                        a.attempts_allowed = new_attempts
                        a.save(update_fields=["attempts_allowed"]) 
            except Exception:
                pass
            meta_form = AssignmentMetaForm(request.POST, instance=a) 
            if meta_form.is_valid(): 
                meta_form.save()
                # Recompute grades if attempts policy changed
                a.refresh_from_db(fields=["attempts_policy"])
                if a.attempts_policy != old_policy:
                    recalc_grades_for_assignment(a)
                messages.success(request, "Assignment details updated.") 
                return redirect("assignments:quiz-manage", pk=a.pk) 
        elif action == "set_available_now":
            a.available_from = timezone.now()
            a.save(update_fields=["available_from"]) 
            messages.success(request, "Availability set to now.")
            return redirect("assignments:quiz-manage", pk=a.pk)
        elif action == "set_deadline_delta":
            delta_str = (request.POST.get("deadline_delta") or "").strip()
            mapping = {
                "1d": timedelta(days=1),
                "3d": timedelta(days=3),
                "1w": timedelta(weeks=1),
                "2w": timedelta(weeks=2),
                "1m": timedelta(days=30),
                "3m": timedelta(days=90),
            }
            td = mapping.get(delta_str)
            if td is None:
                messages.error(request, "Invalid deadline option.")
                return redirect("assignments:quiz-manage", pk=a.pk)
            # Prefer posted available_from value if provided in the form
            try:
                tmp_form = AssignmentMetaForm(request.POST, instance=a)
                if tmp_form.is_valid():
                    base = tmp_form.cleaned_data.get("available_from") or a.available_from or timezone.now()
                else:
                    base = a.available_from or timezone.now()
            except Exception:
                base = a.available_from or timezone.now()
            a.deadline = base + td
            a.save(update_fields=["deadline"]) 
            messages.success(request, "Deadline updated.")
            return redirect("assignments:quiz-manage", pk=a.pk)
        elif action == "toggle_add_correct":
            request.session[toggle_key] = not add_mark_correct
            request.session.modified = True
            try:
                qid = int(request.POST.get("question_id")) if request.POST.get("question_id") else None
            except Exception:
                qid = None
            url = reverse("assignments:quiz-manage", args=[a.pk])
            if qid:
                return redirect(f"{url}?expand=q{qid}")
            return redirect(url)
        elif action == "update_question": 
            qid = int(request.POST.get("question_id", "0")) 
            txt = (request.POST.get("text") or "").strip()
            q = a.questions.filter(pk=qid).first()
            if q and txt:
                q.text = txt
                q.save(update_fields=["text"])
                messages.success(request, "Question updated.")
                url = reverse("assignments:quiz-manage", args=[a.pk])
                return redirect(f"{url}?expand=q{qid}#q{qid}-edit")
        elif action == "move_question":
            qid = int(request.POST.get("question_id", "0"))
            direction = (request.POST.get("dir") or "").strip().lower()
            q = a.questions.filter(pk=qid).first()
            if q:
                if direction == "up":
                    neigh = a.questions.filter(order__lt=q.order).order_by("-order").first()
                else:
                    neigh = a.questions.filter(order__gt=q.order).order_by("order").first()
                if neigh:
                    q.order, neigh.order = neigh.order, q.order
                    q.save(update_fields=["order"])
                    neigh.save(update_fields=["order"])
            url = reverse("assignments:quiz-manage", args=[a.pk])
            return redirect(f"{url}?expand=q{qid}#q{qid}")
        elif not locked:
            if action == "add_question":
                q_form = QuizQuestionForm(request.POST)
                if q_form.is_valid():
                    q = q_form.save(commit=False)
                    q.assignment = a
                    q.order = (a.questions.aggregate(models.Max("order")) or {}).get("order__max") or 0
                    q.order += 1
                    q.save()
                    messages.success(request, "Question added.")
                    return redirect("assignments:quiz-manage", pk=a.pk)
            elif action == "add_choice": 
                question_id = int(request.POST.get("question_id", "0")) 
                q = a.questions.filter(pk=question_id).first() 
                if q: 
                    c_form = QuizAnswerChoiceForm(request.POST) 
                    if c_form.is_valid(): 
                        c = c_form.save(commit=False) 
                        c.question = q 
                        c.order = (q.choices.aggregate(models.Max("order")) or {}).get("order__max") or 0 
                        c.order += 1 
                        # Use session toggle for mark-correct state
                        c.is_correct = bool(request.session.get(toggle_key, False))
                        c.save() 
                        if c.is_correct: 
                            q.choices.exclude(pk=c.pk).update(is_correct=False) 
                        messages.success(request, "Answer option added.") 
                        url = reverse("assignments:quiz-manage", args=[a.pk])
                        return redirect(f"{url}?expand=q{q.id}#c{c.id}") 
            elif action == "update_choice":
                cid = int(request.POST.get("choice_id", "0"))
                ch = QuizAnswerChoice.objects.filter(pk=cid, question__assignment=a).first()
                if ch:
                    new_text = (request.POST.get("text") or "").strip()
                    new_expl = (request.POST.get("explanation") or "").strip()
                    if new_text:
                        ch.text = new_text
                        ch.explanation = new_expl
                        ch.save(update_fields=["text", "explanation"])
                        messages.success(request, "Answer updated.")
                # Save and continue editing support
                if (request.POST.get("continue") or "") == "1":
                    url = reverse("assignments:quiz-manage", args=[a.pk])
                    qid = ch.question_id if ch else None
                    if qid:
                        return redirect(f"{url}?expand=q{qid}&edit_choice={cid}#c{cid}")
                    return redirect(f"{url}?edit_choice={cid}#c{cid}")
                url = reverse("assignments:quiz-manage", args=[a.pk])
                qid = ch.question_id if ch else None
                if qid:
                    return redirect(f"{url}?expand=q{qid}#c{cid}")
                return redirect(f"{url}#c{cid}")
            elif action == "move_choice":
                cid = int(request.POST.get("choice_id", "0"))
                direction = (request.POST.get("dir") or "").strip().lower()
                ch = QuizAnswerChoice.objects.filter(pk=cid, question__assignment=a).select_related("question").first()
                if ch:
                    q = ch.question
                    if direction == "up":
                        neigh = q.choices.filter(order__lt=ch.order).order_by("-order").first()
                    else:
                        neigh = q.choices.filter(order__gt=ch.order).order_by("order").first()
                    if neigh:
                        ch.order, neigh.order = neigh.order, ch.order
                        ch.save(update_fields=["order"])
                        neigh.save(update_fields=["order"])
                url = reverse("assignments:quiz-manage", args=[a.pk])
                if ch:
                    return redirect(f"{url}?expand=q{ch.question_id}#c{ch.id}")
                return redirect(url)
            elif action == "delete_question":
                qid = int(request.POST.get("question_id", "0"))
                q = a.questions.filter(pk=qid).first()
                if q:
                    q.delete()
                    messages.success(request, "Question removed.")
                    return redirect("assignments:quiz-manage", pk=a.pk)
            elif action == "delete_choice": 
                cid = int(request.POST.get("choice_id", "0")) 
                ch = QuizAnswerChoice.objects.filter(pk=cid, question__assignment=a).first() 
                if ch: 
                    # Prevent removing below 2 options on published quizzes
                    q = ch.question
                    if a.is_published and q.choices.count() <= 2:
                        messages.error(request, "Cannot delete: a published question must have at least two choices.")
                        url = reverse("assignments:quiz-manage", args=[a.pk])
                        return redirect(f"{url}?expand=q{q.id}#q{q.id}")
                    ch.delete() 
                    messages.success(request, "Answer option removed.") 
                    url = reverse("assignments:quiz-manage", args=[a.pk])
                    return redirect(f"{url}?expand=q{q.id}#q{q.id}") 
            elif action == "mark_correct":
                cid = int(request.POST.get("choice_id", "0"))
                ch = QuizAnswerChoice.objects.filter(pk=cid, question__assignment=a).select_related("question").first()
                if ch:
                    QuizAnswerChoice.objects.filter(question=ch.question).update(is_correct=False)
                    ch.is_correct = True
                    ch.save(update_fields=["is_correct"])
                    messages.success(request, "Marked as correct.")
                    url = reverse("assignments:quiz-manage", args=[a.pk])
                    return redirect(f"{url}?expand=q{ch.question_id}#c{ch.id}")
            elif action == "publish": 
                if not ready_info["ready"]: 
                    messages.error(request, "Quiz is not ready; fix issues before publishing.") 
                else: 
                    # Default dates: set availability to now and deadline to one week after if not set
                    if not a.available_from:
                        a.available_from = timezone.now()
                    if not a.deadline:
                        base = a.available_from or timezone.now()
                        a.deadline = base + timedelta(days=7)
                    a.is_published = True 
                    a.save(update_fields=["available_from", "deadline", "is_published"]) 
                    messages.success(request, "Quiz published.") 
                return redirect("assignments:quiz-manage", pk=a.pk) 
            elif action == "unpublish":
                if Attempt.objects.filter(assignment=a).exists():
                    messages.error(request, "Cannot unpublish: attempts exist.")
                else:
                    a.is_published = False
                    a.save(update_fields=["is_published"])
                    messages.success(request, "Quiz unpublished.")
                return redirect("assignments:quiz-manage", pk=a.pk)
    return render(request, "assignments/quiz_manage.html", {"assignment": a, "locked": locked, "q_form": q_form, "c_form": c_form, "ready_info": ready_info, "meta_form": meta_form, "attempts_count": attempts_count, "add_mark_correct": add_mark_correct, "edit_choice_id": edit_choice_id, "questions": questions}) 


@login_required
def assignment_take(request, pk: int): 
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    # Permission: enrolled or owner
    if not (_is_enrolled(request.user, a.course) or _is_teacher_owner(request.user, a.course)):
        raise PermissionDenied
    # Availability/deadline/attempts check (only enforced for students) 
    owner = _is_teacher_owner(request.user, a.course) 
    if not owner:
        if not a.is_published:
            messages.error(request, "Assignment is not published.")
            return redirect("assignments:course", course_id=a.course_id)
        if a.is_published and a.available_from and timezone.now() < a.available_from:
            messages.error(request, "Assignment is not available yet.")
            return redirect("assignments:course", course_id=a.course_id)
        if a.deadline and timezone.now() >= a.deadline: 
            messages.error(request, "Deadline has passed.") 
            return redirect("assignments:course", course_id=a.course_id) 
        used = Attempt.objects.filter(assignment=a, student=request.user).count() 
        if used >= a.attempts_allowed: 
            messages.error(request, "No attempts left.") 
            return redirect("assignments:course", course_id=a.course_id) 
    if a.type == AssignmentType.QUIZ: 
        if not a.is_published: 
            messages.error(request, "Assignment is not published.") 
            return redirect("assignments:course", course_id=a.course_id) 
        qs = a.questions.prefetch_related("choices") 
        # Validate quiz readiness: at least 1 question, each has exactly 1 correct
        if qs.count() == 0:
            messages.error(request, "Quiz has no questions yet.")
            return redirect("assignments:course", course_id=a.course_id)
        for q in qs:
            if q.choices.filter(is_correct=True).count() != 1:
                messages.error(request, "Quiz is not ready (each question must have exactly one correct answer).")
                return redirect("assignments:course", course_id=a.course_id)
            if q.choices.count() < 2:
                messages.error(request, "Quiz is not ready (each question must have at least two answer choices).")
                return redirect("assignments:course", course_id=a.course_id)
        used = Attempt.objects.filter(assignment=a, student=request.user).count()
        left = max(0, a.attempts_allowed - used)
        return render(request, "assignments/take_quiz.html", {"assignment": a, "questions": qs, "attempts_used": used, "attempts_left": left}) 
    if a.type == AssignmentType.PAPER: 
        used = Attempt.objects.filter(assignment=a, student=request.user).count()
        left = max(0, a.attempts_allowed - used)
        return render(request, "assignments/take_paper.html", {"assignment": a, "attempts_used": used, "attempts_left": left}) 
    if a.type == AssignmentType.EXAM: 
        used = Attempt.objects.filter(assignment=a, student=request.user).count()
        left = max(0, a.attempts_allowed - used)
        return render(request, "assignments/take_exam.html", {"assignment": a, "questions": a.questions.all(), "attempts_used": used, "attempts_left": left}) 
    used = Attempt.objects.filter(assignment=a, student=request.user).count()
    left = max(0, a.attempts_allowed - used)
    return render(request, "assignments/take_generic.html", {"assignment": a, "attempts_used": used, "attempts_left": left}) 


@login_required
def assignment_submit(request, pk: int): 
    if request.method != "POST":
        return redirect("assignments:take", pk=pk)
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    if not _is_enrolled(request.user, a.course): 
        raise PermissionDenied 
    # Enforce availability, deadline and attempts 
    if not a.is_published:
        messages.error(request, "Assignment is not published.")
        return redirect("assignments:course", course_id=a.course_id)
    if a.available_from and timezone.now() < a.available_from:
        messages.error(request, "Assignment is not available yet.")
        return redirect("assignments:course", course_id=a.course_id)
    if a.deadline and timezone.now() >= a.deadline: 
        messages.error(request, "Deadline has passed.") 
        return redirect("assignments:course", course_id=a.course_id) 
    used = Attempt.objects.filter(assignment=a, student=request.user).count()
    if used >= a.attempts_allowed:
        messages.error(request, "No attempts left.")
        return redirect("assignments:course", course_id=a.course_id)

    attempt = Attempt.objects.create(assignment=a, student=request.user, attempt_no=used + 1, submitted_at=timezone.now())
    if a.type == AssignmentType.QUIZ:
        # Expect POST vars: answer_<question.id> = choice.id
        selected: dict[int, int] = {}
        for q in a.questions.all():
            key = f"answer_{q.id}"
            val = request.POST.get(key)
            if not val:
                messages.error(request, "Please answer all questions.")
                attempt.delete()
                return redirect("assignments:take", pk=a.pk)
            try:
                cid = int(val)
            except Exception:
                messages.error(request, "Invalid answer selection.")
                attempt.delete()
                return redirect("assignments:take", pk=a.pk)
            # Validate that choice belongs to question
            if not QuizAnswerChoice.objects.filter(pk=cid, question=q).exists():
                messages.error(request, "Invalid answer selection.")
                attempt.delete()
                return redirect("assignments:take", pk=a.pk)
            StudentAnswer.objects.create(attempt=attempt, question=q, choice_id=cid)
            selected[q.id] = cid
        res = grade_quiz(a, selected)
        attempt.score = res["score"]
        # Compute marks and release; upsert grade for best-of policy
        attempt.marks_awarded = round((attempt.score or 0.0) / 100.0 * float(a.max_marks or 100.0), 2)
        attempt.released = True
        attempt.released_at = timezone.now()
        attempt.save(update_fields=["score", "marks_awarded", "released", "released_at"]) 
        upsert_grade_for_attempt(attempt, release=True)
        # Notify student of auto-released quiz marks
        try:
            Notification.objects.create(
                user=request.user,
                actor=None,
                type=Notification.TYPE_GRADE,
                course=a.course,
                message=f"Grade released for {a.title}: {attempt.marks_awarded}/{a.max_marks}",
            )
        except Exception:
            pass
        return redirect("assignments:feedback", attempt_id=attempt.id)
    if a.type == AssignmentType.PAPER:
        # Expect file under 'submission_file'
        f = request.FILES.get("submission_file")
        if not f:
            messages.error(request, "Please upload a file.")
            attempt.delete()
            return redirect("assignments:take", pk=a.pk)
        # Basic validation: size and mime
        maxb = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 25 * 1024 * 1024)
        if getattr(f, "size", 0) > maxb:
            messages.error(request, "File too large.")
            attempt.delete()
            return redirect("assignments:take", pk=a.pk)
        ctype = getattr(f, "content_type", "")
        allowed = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        if ctype not in allowed:
            messages.error(request, "Unsupported file type. Please upload PDF or Word document.")
            attempt.delete()
            return redirect("assignments:take", pk=a.pk)
        from .models import StudentFileSubmission
        StudentFileSubmission.objects.create(attempt=attempt, file=f)
        return redirect("assignments:feedback", attempt_id=attempt.id)
    if a.type == AssignmentType.EXAM:
        # Require at least some text for each question
        for q in a.questions.all():
            key = f"text_{q.id}"
            txt = (request.POST.get(key) or "").strip()
            if not txt:
                messages.error(request, "Please answer all questions.")
                attempt.delete()
                return redirect("assignments:take", pk=a.pk)
            from .models import StudentTextAnswer
            StudentTextAnswer.objects.create(attempt=attempt, question=q, text=txt)
        return redirect("assignments:feedback", attempt_id=attempt.id)
    return redirect("assignments:feedback", attempt_id=attempt.id)


@login_required
def attempt_feedback(request, attempt_id: int):
    att = get_object_or_404(Attempt.objects.select_related("assignment", "student", "assignment__course"), pk=attempt_id)
    a = att.assignment
    # Permissions: student who submitted, or course owner
    if not (att.student_id == request.user.id or _is_teacher_owner(request.user, a.course)):
        raise PermissionDenied
    ctx = {"attempt": att, "assignment": a}
    if a.type == AssignmentType.QUIZ:
        # Build mapping for per-question correctness
        answers = {sa.question_id: sa.choice_id for sa in att.answers.select_related("question", "choice")}
        res = grade_quiz(a, answers)
        ctx.update({"questions": a.questions.prefetch_related("choices"), "answers": answers, "perq": res["per_question"], "score": res["score"]})
        return render(request, "assignments/feedback_quiz.html", ctx)
    return render(request, "assignments/feedback_generic.html", ctx)


@login_required
@role_required(Role.TEACHER)
def assignment_attempts(request, pk: int):
    """List attempts for an assignment (teacher view).

    - For Paper/Exam: visible after deadline; used for marking and release.
    - For Quiz: available for manual override of marks (optional), though quiz marks are auto-released on submit.
    """
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    if not _is_teacher_owner(request.user, a.course):
        raise PermissionDenied
    now = timezone.now()
    if a.type in (AssignmentType.PAPER, AssignmentType.EXAM):
        if a.deadline and now < a.deadline:
            messages.error(request, "Attempts list is available after the deadline.")
            return redirect("assignments:manage", pk=a.pk if a.type != AssignmentType.QUIZ else a.pk)
    attempts = (
        Attempt.objects.filter(assignment=a)
        .select_related("student")
        .order_by("student__username", "submitted_at")
    )
    grade_form = GradeAttemptForm()
    return render(request, "assignments/attempts_list.html", {"assignment": a, "attempts": attempts, "grade_form": grade_form, "now": now})


@login_required
@role_required(Role.TEACHER)
def attempt_grade(request, attempt_id: int):
    att = get_object_or_404(Attempt.objects.select_related("assignment", "student", "assignment__course"), pk=attempt_id)
    a = att.assignment
    if not _is_teacher_owner(request.user, a.course):
        raise PermissionDenied
    # Paper/Exam grading allowed after deadline; Quiz override allowed anytime
    if a.type in (AssignmentType.PAPER, AssignmentType.EXAM):
        if a.deadline and timezone.now() < a.deadline:
            messages.error(request, "Cannot grade before the deadline.")
            return redirect("assignments:attempts", pk=a.pk)
    if request.method != "POST":
        return redirect("assignments:attempts", pk=a.pk)
    form = GradeAttemptForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid grading input.")
        return redirect("assignments:attempts", pk=a.pk)
    marks_awarded = float(form.cleaned_data["marks_awarded"])
    feedback_text = form.cleaned_data.get("feedback_text") or ""
    override_reason = form.cleaned_data.get("override_reason") or ""
    # Bounds check
    max_marks = float(a.max_marks or 100.0)
    if marks_awarded < 0 or marks_awarded > max_marks:
        messages.error(request, f"Marks must be between 0 and {max_marks}.")
        return redirect("assignments:attempts", pk=a.pk)
    # For quiz override, require reason if changing from auto grade
    if a.type == AssignmentType.QUIZ:
        auto_marks = round((float(att.score or 0.0) / 100.0) * max_marks, 2) if att.score is not None else None
        if auto_marks is not None and round(marks_awarded, 2) != round(auto_marks, 2) and not override_reason.strip():
            messages.error(request, "Override requires a reason.")
            return redirect("assignments:attempts", pk=a.pk)

    # Persist grading
    att.marks_awarded = marks_awarded
    att.feedback_text = feedback_text
    att.override_reason = override_reason
    att.graded_by = request.user
    att.graded_at = timezone.now()
    # Release immediately for both manual grading and overrides
    att.released = True
    att.released_at = timezone.now()
    att.save(update_fields=["marks_awarded", "feedback_text", "override_reason", "graded_by", "graded_at", "released", "released_at"])

    upsert_grade_for_attempt(att, release=True)

    # Notify student on release
    try:
        Notification.objects.create(
            user=att.student,
            actor=request.user,
            type=Notification.TYPE_GRADE,
            course=a.course,
            message=f"Grade released for {a.title}: {att.marks_awarded}/{a.max_marks}",
        )
    except Exception:
        pass

    messages.success(request, "Grade saved and released.")
    return redirect("assignments:attempts", pk=a.pk)


@login_required
@role_required(Role.TEACHER)
def assignment_manage(request, pk: int):
    """Generic manage view for Paper/Exam assignments.

    - Paper: manage meta (title, availability, deadline, attempts), publish/unpublish.
    - Exam: same as Paper, plus text-only question add/edit/delete. Locked when attempts exist.
    """
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    if a.type == AssignmentType.QUIZ:
        return redirect("assignments:quiz-manage", pk=pk)
    if not _is_teacher_owner(request.user, a.course):
        raise PermissionDenied

    locked = Attempt.objects.filter(assignment=a).exists()
    attempts_count = Attempt.objects.filter(assignment=a).count()
    meta_form = AssignmentMetaForm(instance=a)
    q_form = QuizQuestionForm()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "update_meta":
            # Apply attempts update defensively even if other fields are invalid
            old_policy = a.attempts_policy
            try:
                new_attempts = int((request.POST.get("attempts_allowed") or "").strip() or 0)
                if new_attempts >= 1:
                    used = Attempt.objects.filter(assignment=a).count()
                    if new_attempts >= used and new_attempts != a.attempts_allowed:
                        a.attempts_allowed = new_attempts
                        a.save(update_fields=["attempts_allowed"]) 
            except Exception:
                pass
            meta_form = AssignmentMetaForm(request.POST, instance=a)
            if meta_form.is_valid():
                meta_form.save()
                a.refresh_from_db(fields=["attempts_policy"])
                if a.attempts_policy != old_policy:
                    recalc_grades_for_assignment(a)
                messages.success(request, "Assignment details updated.")
                return redirect("assignments:manage", pk=a.pk)
        elif action == "set_available_now":
            a.available_from = timezone.now()
            a.save(update_fields=["available_from"])
            messages.success(request, "Availability set to now.")
            return redirect("assignments:manage", pk=a.pk)
        elif action == "set_deadline_delta":
            delta_str = (request.POST.get("deadline_delta") or "").strip()
            mapping = {
                "1d": timedelta(days=1),
                "3d": timedelta(days=3),
                "1w": timedelta(weeks=1),
                "2w": timedelta(weeks=2),
                "1m": timedelta(days=30),
                "3m": timedelta(days=90),
            }
            td = mapping.get(delta_str)
            if td is None:
                messages.error(request, "Invalid deadline option.")
                return redirect("assignments:manage", pk=a.pk)
            try:
                tmp_form = AssignmentMetaForm(request.POST, instance=a)
                if tmp_form.is_valid():
                    base = tmp_form.cleaned_data.get("available_from") or a.available_from or timezone.now()
                else:
                    base = a.available_from or timezone.now()
            except Exception:
                base = a.available_from or timezone.now()
            a.deadline = base + td
            a.save(update_fields=["deadline"]) 
            messages.success(request, "Deadline updated.")
            return redirect("assignments:manage", pk=a.pk)
        elif not locked and a.type == AssignmentType.EXAM:
            if action == "add_question":
                q_form = QuizQuestionForm(request.POST)
                if q_form.is_valid():
                    q = q_form.save(commit=False)
                    q.assignment = a
                    q.order = (a.questions.aggregate(models.Max("order")) or {}).get("order__max") or 0
                    q.order += 1
                    q.save()
                    messages.success(request, "Question added.")
                    return redirect("assignments:manage", pk=a.pk)
            elif action == "update_question":
                qid = int(request.POST.get("question_id", "0"))
                txt = (request.POST.get("text") or "").strip()
                q = a.questions.filter(pk=qid).first()
                if q and txt:
                    q.text = txt
                    q.save(update_fields=["text"])
                    messages.success(request, "Question updated.")
                    return redirect("assignments:manage", pk=a.pk)
            elif action == "delete_question":
                qid = int(request.POST.get("question_id", "0"))
                q = a.questions.filter(pk=qid).first()
                if q:
                    q.delete()
                    messages.success(request, "Question removed.")
                    return redirect("assignments:manage", pk=a.pk)
        elif action == "publish":
            # Default dates: set availability to now and deadline to one week after if not set
            if not a.available_from:
                a.available_from = timezone.now()
            if not a.deadline:
                base = a.available_from or timezone.now()
                a.deadline = base + timedelta(days=7)
            a.is_published = True
            a.save(update_fields=["available_from", "deadline", "is_published"])
            messages.success(request, "Assignment published.")
            return redirect("assignments:manage", pk=a.pk)
        elif action == "unpublish":
            if Attempt.objects.filter(assignment=a).exists():
                messages.error(request, "Cannot unpublish: attempts exist.")
            else:
                a.is_published = False
                a.save(update_fields=["is_published"])
                messages.success(request, "Assignment unpublished.")
            return redirect("assignments:manage", pk=a.pk)

    return render(
        request,
        "assignments/manage_generic.html",
        {"assignment": a, "locked": locked, "meta_form": meta_form, "q_form": q_form, "attempts_count": attempts_count},
    )
