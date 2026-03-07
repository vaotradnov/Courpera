"""Course list/detail and enrolment actions (Stage 5)."""

from __future__ import annotations

import re
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Avg, Case, CharField, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Concat, Length, Substr
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from accounts.decorators import role_required
from accounts.models import Role
from assignments.models import Assignment, Attempt, Grade
from assignments.utils import compute_course_percentage

from .forms import AddStudentForm, CourseForm, SyllabusForm
from .forms_feedback import FeedbackForm
from .gradebook import build_grade_rows, gradebook_csv_response
from .models import Course, Enrolment
from .models_feedback import Feedback


def _is_enrolled(user, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return Enrolment.objects.filter(course=course, student=user).exists()


def _wrap_cache_if_enabled(view_func):
    """Wrap the view with cache_page when catalogue cache is enabled.

    Using a post-definition wrapper avoids mypy/django-stubs crashes on
    callable decorators like `@_catalogue_cache_decorator()`.
    """
    try:
        enabled = getattr(settings, "CATALOGUE_CACHE_ENABLED", True)
        seconds = int(getattr(settings, "CATALOGUE_CACHE_SECONDS", 60))
    except Exception:
        enabled = True
        seconds = 60
    if not enabled:
        return view_func
    return cache_page(seconds)(view_func)


@vary_on_cookie
def _course_list_impl(request: HttpRequest) -> HttpResponse:
    """Public course catalogue with simple filters and sorting (16.04).

    Filters: subject, level, language via query params.
    Sorting: sort in {relevance|enrolled|updated|title}. Default relevance when q provided else title.
    """
    q = (request.GET.get("q") or "").strip()
    subject = (request.GET.get("subject") or "").strip()
    level = (request.GET.get("level") or "").strip()
    language = (request.GET.get("language") or "").strip()
    sort = (request.GET.get("sort") or "").strip().lower()

    courses = Course.objects.select_related("owner")
    # Split annotations to avoid mypy plugin inference issues
    courses = courses.annotate(enrol_count=Count("enrolments", distinct=True))
    courses = courses.annotate(rating=Avg("feedback__rating"))
    if q:
        courses = courses.filter(
            Q(title__icontains=q) | Q(owner__username__icontains=q) | Q(description__icontains=q)
        )
        # naive relevance: title match ranks higher
        courses = courses.annotate(
            rel=Case(
                When(title__icontains=q, then=Value(2)),
                When(description__icontains=q, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    if subject:
        courses = courses.filter(subject__iexact=subject)
    if level:
        courses = courses.filter(level__iexact=level)
    if language:
        courses = courses.filter(language__iexact=language)

    if sort == "enrolled":
        courses = courses.order_by(F("enrol_count").desc(nulls_last=True), "title")
    elif sort == "updated":
        courses = courses.order_by(F("updated_at").desc())
    elif sort == "relevance" and q:
        courses = courses.order_by(F("rel").desc(), F("updated_at").desc())
    else:
        # Default: relevance if q else title
        courses = courses.order_by(F("rel").desc()) if q else courses.order_by("title")

    enrolled_ids = set()
    if request.user.is_authenticated:
        enrolled_ids = set(
            Enrolment.objects.filter(student_id=request.user.id).values_list("course_id", flat=True)
        )
    # Pagination (9 per page works well with a 3-column grid)
    try:
        page_number = int(request.GET.get("page") or 1)
        if page_number < 1:
            page_number = 1
    except Exception:
        page_number = 1
    paginator = Paginator(courses, 9)
    page_obj = paginator.get_page(page_number)
    total = paginator.count  # reuse paginator's cached count; avoid duplicate COUNT(*) query
    ctx = {
        "courses": page_obj.object_list,
        "paginator": paginator,
        "page_obj": page_obj,
        "page": page_obj.number,
        "enrolled_ids": enrolled_ids,
        "role": getattr(getattr(request.user, "profile", None), "role", None),
        "q": q,
        "subject": subject,
        "level": level,
        "language": language,
        "sort": sort or ("relevance" if q else "title"),
        "total": total,
    }
    return render(request, "courses/list.html", ctx)


# Apply cache wrapper after definition to keep type checkers happy
course_list: Callable[[HttpRequest], HttpResponse]
course_list = _wrap_cache_if_enabled(_course_list_impl)


def _catalogue_cache_decorator():  # Backwards-compat for tests
    try:
        enabled = getattr(settings, "CATALOGUE_CACHE_ENABLED", True)
        seconds = int(getattr(settings, "CATALOGUE_CACHE_SECONDS", 60))
    except Exception:
        enabled = True
        seconds = 60
    if not enabled:

        def identity(fn):
            return fn

        return identity
    return cache_page(seconds)


@login_required
@role_required(Role.TEACHER)
def course_create(request: HttpRequest) -> HttpResponse:
    """Teacher-only course creation."""
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            messages.success(request, "Course created.")
            return redirect("courses:detail", pk=course.pk)
    else:
        form = CourseForm()
    return render(request, "courses/create.html", {"form": form})


@login_required
@role_required(Role.TEACHER)
def course_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Teacher-only edit of course title/description (owner only)."""
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated.")
            return redirect("courses:detail", pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(request, "courses/create.html", {"form": form, "is_edit": True, "course": course})


@login_required
def course_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Course detail restricted to owner or enrolled students."""
    course = get_object_or_404(Course.objects.select_related("owner"), pk=pk)
    owner_view = course.is_owner(request.user)
    is_enrolled = _is_enrolled(request.user, course)
    # Allow non-enrolled students to see a limited view (title, teacher, feedback list).
    limited_view = not (owner_view or is_enrolled)

    # For teachers, show roster; for students, show a concise message.
    roster = None
    add_form = None
    feedback_form = None
    if owner_view:
        roster = (
            Enrolment.objects.filter(course=course)
            .select_related("student")
            .order_by("student__username")
        )
        add_form = AddStudentForm()
    if is_enrolled:
        # Initialise form with existing feedback if present
        existing = Feedback.objects.filter(course=course, student_id=request.user.id).first()
        feedback_form = FeedbackForm(instance=existing)

    # Prepare syllabus/outcomes lines for rendering
    def _split_lines(s: str) -> list[str]:
        return [line.strip() for line in (s or "").splitlines() if line.strip()]

    # Compute assignment availability and readiness for display
    assignments = Assignment.objects.filter(course=course, is_published=True).order_by("title")
    now = __import__("datetime").datetime.now(tz=None)
    # Use Django timezone to avoid naive
    from django.utils import timezone as _tz

    now = _tz.now()
    ann = []
    for a in assignments:
        if a.type == "quiz":
            from assignments.utils import quiz_readiness

            a.ready_info = quiz_readiness(a)
        else:
            a.ready_info = None
        a.avail_ok = a.available_from is None or now >= a.available_from
        ann.append(a)

    # Attempts left for enrolled students
    if is_enrolled and not owner_view:
        ids = [a.id for a in ann]
        if ids:
            from django.db.models import Count as _Count

            used = (
                Attempt.objects.filter(assignment_id__in=ids, student_id=request.user.id)
                .values("assignment_id")
                .annotate(c=_Count("id"))
            )
            used_map = {row["assignment_id"]: row["c"] for row in used}
            for a in ann:
                u = used_map.get(a.id, 0)
                a.attempts_used = u
                a.attempts_left = max(0, (a.attempts_allowed or 0) - u)

    # Student grades summary for this course (if enrolled)
    student_grades = None
    if is_enrolled and not owner_view:
        released = (
            Grade.objects.filter(
                course=course,
                student_id=request.user.id,
                assignment__is_published=True,
                released_at__isnull=False,
            )
            .select_related("assignment")
            .order_by("assignment__title")
        )
        total_pct = compute_course_percentage(course, request.user, only_released=True)
        student_grades = {"grades": released, "percent": total_pct}

    ctx = {
        "course": course,
        "owner_view": owner_view,
        "is_enrolled": is_enrolled,
        "limited_view": limited_view,
        "roster": roster,
        "add_form": add_form,
        "feedback_form": feedback_form,
        "feedback_list": Feedback.objects.filter(course=course).select_related("student"),
        # Show published assignments on course page for both teacher and enrolled students
        "assignments": ann,
        "student_grades": student_grades,
        "syllabus_lines": _split_lines(getattr(course, "syllabus", "")),
        "outcome_lines": _split_lines(getattr(course, "outcomes", "")),
        "enrol_count": Enrolment.objects.filter(course=course).count(),
        "next_deadline": next((a.deadline for a in ann if getattr(a, "deadline", None)), None),
        "breadcrumbs": [
            ("/", "Home"),
            ("/courses/", "Courses"),
            ("", course.title),
        ],
    }
    return render(request, "courses/detail.html", ctx)


@login_required
@role_required(Role.TEACHER)
def course_syllabus_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Owner-only syllabus/outcomes editing for a course."""
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = SyllabusForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Syllabus updated.")
            return redirect("courses:detail", pk=course.pk)
    else:
        form = SyllabusForm(instance=course)
    return render(request, "courses/syllabus_edit.html", {"form": form, "course": course})


@login_required
@role_required(Role.STUDENT)
def course_enrol(request: HttpRequest, pk: int) -> HttpResponse:
    """Enrol the current student into a course (idempotent)."""
    course = get_object_or_404(Course, pk=pk)
    # Extra defense-in-depth: deny if not a student role
    if getattr(getattr(request.user, "profile", None), "role", None) != Role.STUDENT:
        raise PermissionDenied
    if request.method == "POST":
        try:
            _, created = Enrolment.objects.get_or_create(course=course, student=request.user)
        except Exception:
            # Any validation issues (e.g., non-student) map to forbidden here
            raise PermissionDenied
        if created:
            messages.success(request, "Enrolled in course.")
        return redirect("courses:detail", pk=course.pk)
    return redirect("courses:list")


@login_required
@role_required(Role.TEACHER)
def course_remove_student(request: HttpRequest, pk: int, user_id: int) -> HttpResponse:
    """Teacher removes a student from their course.

    Permission: only the course owner can remove students.
    """
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    if request.method == "POST":
        Enrolment.objects.filter(course=course, student_id=user_id).delete()
        messages.success(request, "Student removed from course.")
    return redirect("courses:detail", pk=course.pk)


@login_required
@role_required(Role.TEACHER)
def course_add_student(request: HttpRequest, pk: int) -> HttpResponse:
    """Teacher enrols a student by username or email (owner only), or searches.

    Behaviour:
    - If the submitted button named 'action' has value 'search', perform a
      partial match search on username/email and render the course detail
      with results.
    - Otherwise, attempt to enrol a single user identified by the query
      (exact username or email match), then redirect back to detail.
    """
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = AddStudentForm(request.POST)
        if form.is_valid():
            q = form.cleaned_data["query"].strip()
            action = request.POST.get("action", "enrol").lower()
            if action == "search":
                # Partial, case-insensitive; support username, email, stored Student ID,
                # and substring matches on zero-padded numeric ID (e.g., '004' => S0000004)
                base = (
                    User.objects.select_related("profile")
                    .annotate(id_str=Cast("id", output_field=CharField()))
                    .annotate(pad=Concat(Value("0000000"), F("id_str")))
                    .annotate(last7=Substr("pad", Length("pad") - Value(6), Value(7)))
                )
                qn = re.sub(r"\D", "", q)
                filt = (
                    Q(username__icontains=q)
                    | Q(email__icontains=q)
                    | Q(profile__student_number__icontains=q)
                )
                if qn:
                    filt = filt | Q(last7__icontains=qn)
                results = (
                    base.filter(filt).filter(profile__role=Role.STUDENT).order_by("username")[:50]
                )
                roster = (
                    Enrolment.objects.filter(course=course)
                    .select_related("student")
                    .order_by("student__username")
                )
                ctx = {
                    "course": course,
                    "owner_view": True,
                    "is_enrolled": False,
                    "roster": roster,
                    "add_form": form,
                    "search_results": results,
                    "searched": True,
                }
                return render(request, "courses/detail.html", ctx)
            # Enrol flow: exact match on username or email
            target = (
                User.objects.select_related("profile").filter(username__iexact=q).first()
                or User.objects.select_related("profile").filter(email__iexact=q).first()
                or User.objects.select_related("profile")
                .filter(profile__student_number__iexact=q)
                .first()
            )
            if not target:
                messages.error(request, "No user found for that username or email.")
                return redirect("courses:detail", pk=course.pk)
            profile = getattr(target, "profile", None)
            if not profile or profile.role != Role.STUDENT:
                messages.error(request, "User is not a student.")
                return redirect("courses:detail", pk=course.pk)
            obj, created = Enrolment.objects.get_or_create(course=course, student=target)
            if created:
                messages.success(request, f"Enrolled {target.username}.")
            else:
                messages.error(request, f"{target.username} is already enrolled.")
    return redirect("courses:detail", pk=course.pk)


@login_required
@role_required(Role.TEACHER)
def course_gradebook(request: HttpRequest, pk: int) -> HttpResponse:
    """Teacher gradebook view: students x assignments matrix with course %.

    Owner-only; lists only published assignments.
    """
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    assignments = list(
        Assignment.objects.filter(course=course, is_published=True).order_by("title")
    )
    enrolments = list(
        Enrolment.objects.filter(course=course)
        .select_related("student", "student__profile")
        .order_by("student__username")
    )
    grade_rows = build_grade_rows(course, assignments)
    # Compute course percent per student using Grades
    per_student_pct: dict[int, float] = {}
    for e in enrolments:
        per_student_pct[e.student_id] = compute_course_percentage(course, e.student)
    return render(
        request,
        "courses/gradebook.html",
        {
            "course": course,
            "assignments": assignments,
            "enrolments": enrolments,
            "grade_rows": grade_rows,
            "course_pct": per_student_pct,
        },
    )


@login_required
@role_required(Role.TEACHER)
def course_gradebook_csv(request: HttpRequest, pk: int) -> HttpResponse:
    """CSV export for gradebook: username, S-ID, each assignment X/Y, course %."""
    course = get_object_or_404(Course, pk=pk)
    if not course.is_owner(request.user):
        raise PermissionDenied
    return gradebook_csv_response(course)


@login_required
@role_required(Role.STUDENT)
def course_unenrol(request: HttpRequest, pk: int) -> HttpResponse:
    """Student unenrols from a course (owner unaffected)."""
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        Enrolment.objects.filter(course=course, student_id=request.user.id).delete()
        messages.success(request, "Unenrolled from course.")
    return redirect("courses:list")


@login_required
@role_required(Role.STUDENT)
def course_feedback(request: HttpRequest, pk: int) -> HttpResponse:
    """Create or update feedback for a course (student-only, enrolled)."""
    course = get_object_or_404(Course, pk=pk)
    if not Enrolment.objects.filter(course=course, student_id=request.user.id).exists():
        messages.error(request, "Please enrol before leaving feedback.")
        return redirect("courses:detail", pk=course.pk)
    if request.method == "POST":
        existing = Feedback.objects.filter(course=course, student_id=request.user.id).first()
        form = FeedbackForm(request.POST, instance=existing)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.course = course
            fb.student = request.user
            fb.save()
            messages.success(request, "Feedback saved.")
        else:
            messages.error(request, "Invalid feedback.")
    return redirect("courses:detail", pk=course.pk)
