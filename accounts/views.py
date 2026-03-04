"""Accounts views: registration, profile edit, and role home pages."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.http import (
    HttpRequest,
    HttpResponse,
    Http404,
    HttpResponseBadRequest,
    FileResponse,
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
from django.db.models import Q
from django.contrib.auth.models import User
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.conf import settings
import hashlib
import re
from urllib.parse import urlencode
from django.contrib.staticfiles import finders

from .decorators import role_required
from .forms import (
    RegistrationForm,
    ProfileForm,
    EmailOrUsernameAuthenticationForm,
    SecretResetForm,
)
from .models import Role
from activity.forms import StatusForm
from activity.models import Status
from courses.models import Enrolment, Course
from assignments.utils import compute_course_percentage
from assignments.models import Grade, Assignment


class CourperaLoginView(LoginView):
    template_name = "registration/login.html"
    form_class = EmailOrUsernameAuthenticationForm

    def post(self, request: HttpRequest, *args, **kwargs):
        # Simple per-session login throttle: max 10 attempts/min to reduce brute force
        try:
            ts = request.session.get("login_ts", [])
            now = __import__("time").time()
            ts = [t for t in ts if now - t < 60]
            if len(ts) >= 10:
                messages.error(request, "Too many login attempts. Please wait a minute and try again.")
                return self.get(request, *args, **kwargs)
            ts.append(now)
            request.session["login_ts"] = ts
        except Exception:
            pass
        return super().post(request, *args, **kwargs)


class CourperaLogoutView(LogoutView):
    next_page = "/"
    # Allow GET to support direct navigation to the logout URL without 405.
    http_method_names = ["get", "post", "head", "options"]
    # Convenience: accept GET as well to avoid 405 when users follow a link.
    # In stricter deployments, prefer POST-only logout.
    def get(self, request, *args, **kwargs):  # pragma: no cover
        return self.post(request, *args, **kwargs)


def register(request: HttpRequest) -> HttpResponse:
    """Register a new user and pick an initial role.

    On success, the user is logged in and redirected to the role-aware
    home view which then routes to student/teacher pages.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Courpera!")
            return redirect("accounts:home")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Dispatch to a role-specific home page."""
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role == Role.TEACHER:
        return redirect("accounts:home-teacher")
    return redirect("accounts:home-student")


@login_required
@role_required(Role.TEACHER)
def home_teacher(request: HttpRequest) -> HttpResponse:
    # 16.04: Teaching dashboard with quick links and enrolment counts
    from django.db.models import Count as _Count
    owned = (
        Course.objects.filter(owner=request.user)
        .annotate(enrol_count=_Count("enrolments"))
        .order_by("title")
    )
    return render(request, "accounts/home_teacher.html", {"owned": owned})


@login_required
@role_required(Role.STUDENT)
def home_student(request: HttpRequest) -> HttpResponse:
    updates = Status.objects.filter(user=request.user)[:20]
    form = StatusForm()
    # 16.04: My Learning dashboard items (upcoming deadlines and resume links)
    from django.utils import timezone as _tz
    enrol_courses = [e.course for e in Enrolment.objects.filter(student=request.user).select_related("course")]
    upcoming: list[dict] = []
    if enrol_courses:
        ids = [c.id for c in enrol_courses]
        qs = (
            Assignment.objects.filter(course_id__in=ids, is_published=True, deadline__isnull=False, deadline__gt=_tz.now())
            .select_related("course")
            .order_by("deadline")[:10]
        )
        for a in qs:
            upcoming.append({"course": a.course, "assignment": a, "deadline": a.deadline})
    return render(request, "accounts/home_student.html", {"updates": updates, "status_form": form, "upcoming": upcoming})


@login_required
@role_required(Role.TEACHER)
def search_users(request: HttpRequest) -> HttpResponse:
    """Teacher-only user search by username, e-mail, or IDs (partial, case-insensitive)."""
    q = (request.GET.get("q") or "").strip()
    results = []
    if q:
        base_q = (
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(profile__student_number__icontains=q)
            | Q(profile__instructor_id__icontains=q)
        )
        # Fallback: support I######## pattern by user id if instructor_id not yet set
        m = re.fullmatch(r"[iI](\d{1,9})", q)
        if m:
            try:
                uid = int(m.group(1))
                base_q = base_q | Q(id=uid)
            except Exception:
                pass
        results = (
            User.objects.select_related("profile")
            .filter(base_q)
            .order_by("username")[:50]
        )
    return render(request, "accounts/search.html", {"q": q, "results": results})


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    if request.method == "POST":
        # Remove uploaded avatar when requested
        if request.POST.get("remove_avatar") == "1":
            if getattr(profile, "avatar", None):
                try:
                    profile.avatar.delete(save=False)
                except Exception:
                    pass
                profile.avatar = None
                profile.save(update_fields=["avatar"])
                messages.success(request, "Avatar removed.")
                return redirect("accounts:profile")
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:home")
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, "accounts/profile.html", {"form": form, "profile_obj": profile})


@login_required
@role_required(Role.STUDENT)
def student_grades(request: HttpRequest) -> HttpResponse:
    """Student grades overview across enrolled courses."""
    enrolments = (
        Enrolment.objects.filter(student=request.user)
        .select_related("course", "course__owner")
        .order_by("course__title")
    )
    rows = []
    for e in enrolments:
        pct = compute_course_percentage(e.course, request.user, only_released=True)
        grades = (
            Grade.objects.filter(
                course=e.course,
                student=request.user,
                assignment__is_published=True,
                released_at__isnull=False,
            )
            .select_related("assignment")
            .order_by("assignment__title")
        )
        rows.append({"course": e.course, "percent": pct, "grades": grades})
    return render(request, "accounts/grades.html", {"rows": rows})


class CourperaPasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = "/accounts/password/change/done/"


@login_required
def password_change_done(request: HttpRequest) -> HttpResponse:
    return render(request, "registration/password_change_done.html")


def password_forgot(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        # Throttle: limit to 5 attempts per 10 minutes per session
        ts = request.session.get("pw_reset_ts", [])
        now = __import__("time").time()
        ts = [t for t in ts if now - t < 600]
        if len(ts) >= 5:
            messages.error(request, "Too many reset attempts. Please wait and try again.")
            return render(request, "accounts/password_forgot.html", {"form": SecretResetForm()})
        form = SecretResetForm(request.POST)
        if form.is_valid():
            ident = (form.cleaned_data["identifier"] or "").strip()
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            user = UserModel.objects.filter(username__iexact=ident).first() or UserModel.objects.filter(email__iexact=ident).first()
            if not user:
                messages.error(request, "Account not found.")
            else:
                prof = getattr(user, "profile", None)
                from django.contrib.auth.hashers import check_password
                ok = bool(prof and prof.secret_word_hash and check_password(form.cleaned_data["secret_word"], prof.secret_word_hash))
                if not ok:
                    messages.error(request, "Secret word does not match.")
                else:
                    user.set_password(form.cleaned_data["new_password1"])
                    user.save(update_fields=["password"])
                    messages.success(request, "Password has been reset. You can now sign in.")
                    ts.append(now)
                    request.session["pw_reset_ts"] = ts
                    return redirect("accounts:login")
        ts.append(now)
        request.session["pw_reset_ts"] = ts
    else:
        form = SecretResetForm()
    return render(request, "accounts/password_forgot.html", {"form": form})


@require_GET
def avatar_proxy(request: HttpRequest, user_id: int, size: int) -> HttpResponse:
    """Proxy DiceBear avatar as same-origin PNG to avoid ORB issues.

    Accepts deterministic query params but recomputes seed server-side.
    """
    try:
        size = int(size)
    except Exception:  # pragma: no cover
        return HttpResponseBadRequest("invalid size")
    if size < 16 or size > 256:
        return HttpResponseBadRequest("invalid size")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:  # pragma: no cover - edge
        raise Http404("user not found") from exc

    # Compute deterministic seed; vary by profile role to produce distinct defaults
    role = getattr(getattr(user, "profile", None), "role", "student")
    seed_src = f"{getattr(user, 'pk', '0')}:{getattr(settings, 'AVATAR_SEED_SALT', 'courpera')}:{role}"
    seed = hashlib.sha256(seed_src.encode()).hexdigest()

    # Serve role-specific default avatar from local static to avoid network dependency
    img_name = "avatar-default.svg" if role == "student" else "avatar-teacher.svg"
    rel_path = f"img/{img_name}"
    abs_path = finders.find(rel_path)
    if not abs_path:
        return HttpResponseBadRequest("avatar asset missing")
    # Stream the static file for reliable decoding and caching
    resp = FileResponse(open(abs_path, "rb"), content_type="image/svg+xml")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp
