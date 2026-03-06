"""REST API v1 viewsets and endpoints (Stage 8)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from activity.models import Status
from courses.models import Course, Enrolment
from courses.models_feedback import Feedback
from materials.models import Material

from .permissions import IsAuthenticatedOrReadOnly, IsTeacher
from .serializers import (
    CourseSerializer,
    EnrolmentSerializer,
    FeedbackSerializer,
    MaterialSerializer,
    StatusSerializer,
    UserSerializer,
)

User = get_user_model()


def _is_owner(user, course: Course) -> bool:
    return bool(user and user.is_authenticated and course.owner_id == user.id)


def _is_enrolled(user, course: Course) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return Enrolment.objects.filter(course=course, student_id=user.id).exists()


@extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
)
class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().select_related("profile").order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["username", "email"]
    ordering_fields = ["username", "id"]


@extend_schema_view(
    list=extend_schema(tags=["Courses"]),
    retrieve=extend_schema(tags=["Courses"]),
    create=extend_schema(tags=["Courses"]),
    update=extend_schema(tags=["Courses"]),
    partial_update=extend_schema(tags=["Courses"]),
    destroy=extend_schema(tags=["Courses"]),
)
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related("owner", "owner__profile").all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["title", "description", "owner__username"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def perform_create(self, serializer):
        # Only teachers can create courses; owner is current user
        profile = getattr(self.request.user, "profile", None)
        if getattr(profile, "role", None) != "teacher":
            raise PermissionDenied("Only teachers can create courses.")
        serializer.save(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        if not (_is_owner(request.user, course) or _is_enrolled(request.user, course)):
            return Response(
                {"detail": "Enrol to access this course."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().retrieve(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(tags=["Enrolments"]),
    retrieve=extend_schema(tags=["Enrolments"]),
    create=extend_schema(tags=["Enrolments"]),
    destroy=extend_schema(tags=["Enrolments"]),
)
class EnrolmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrolmentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Students: own enrolments; Teachers: enrolments to their courses
        user = self.request.user
        if not user.is_authenticated:
            return Enrolment.objects.none()
        role = getattr(getattr(user, "profile", None), "role", None)
        base = Enrolment.objects.select_related(
            "course",
            "course__owner",
            "course__owner__profile",
            "student",
            "student__profile",
        )
        course_id = self.request.query_params.get("course")
        if role == "student":
            qs = base.filter(student_id=user.id)
        elif role == "teacher":
            qs = base.filter(course__owner_id=user.id)
        else:
            qs = Enrolment.objects.none()
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        # Student self-enrol only
        profile = getattr(self.request.user, "profile", None)
        if getattr(profile, "role", None) != "student":
            raise PermissionDenied("Only students can enrol.")
        course = serializer.validated_data.get("course")
        # Prevent duplicate enrolments with a friendly 400 instead of DB error
        if Enrolment.objects.filter(course=course, student_id=self.request.user.id).exists():
            raise ValidationError({"detail": "Already enrolled in this course."})
        serializer.save(student=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Student can unenrol self; teacher owner can remove any from own course
        instance = self.get_object()
        user = request.user
        if instance.student_id == user.id:
            return super().destroy(request, *args, **kwargs)
        if _is_owner(user, instance.course):
            return super().destroy(request, *args, **kwargs)
        return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)


@extend_schema_view(
    list=extend_schema(tags=["Materials"]),
    retrieve=extend_schema(tags=["Materials"]),
)
class MaterialViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Owner or enrolled can see materials; otherwise none
        user = self.request.user
        qs = Material.objects.select_related("course").all()
        if not user.is_authenticated:
            return Material.objects.none()
        # Owners can see their course materials; students see where enrolled
        qs = qs.filter(
            Q(course__owner_id=user.id) | Q(course__enrolments__student_id=user.id)
        ).distinct()
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs


@extend_schema_view(
    list=extend_schema(tags=["Feedback"]),
    retrieve=extend_schema(tags=["Feedback"]),
    create=extend_schema(tags=["Feedback"]),
    update=extend_schema(tags=["Feedback"]),
    partial_update=extend_schema(tags=["Feedback"]),
    destroy=extend_schema(tags=["Feedback"]),
)
class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    ordering_fields = ["created_at", "rating"]

    def get_queryset(self):
        course_id = self.request.query_params.get("course")
        qs = Feedback.objects.select_related("course", "student")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        # Only enrolled students may create feedback
        user = self.request.user
        course = serializer.validated_data.get("course")
        if not user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        if getattr(getattr(user, "profile", None), "role", None) != "student":
            raise PermissionDenied("Only students can leave feedback.")
        if not Enrolment.objects.filter(course=course, student_id=user.id).exists():
            raise PermissionDenied("Enrol before leaving feedback.")
        serializer.save(student=user)

    def perform_update(self, serializer):
        # Students may update their own feedback only
        instance = self.get_object()
        if instance.student_id != self.request.user.id:
            raise PermissionDenied("Cannot edit others' feedback.")
        serializer.save()


@extend_schema_view(
    list=extend_schema(tags=["Status"]),
    retrieve=extend_schema(tags=["Status"]),
    create=extend_schema(tags=["Status"]),
    destroy=extend_schema(tags=["Status"]),
)
class StatusViewSet(viewsets.ModelViewSet):
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    ordering_fields = ["created_at", "id"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Status.objects.none()
        # Students: own updates; teachers: none for now (could extend later)
        role = getattr(getattr(user, "profile", None), "role", None)
        if role == "student":
            return Status.objects.filter(user_id=user.id).order_by("-created_at")
        return Status.objects.none()

    def perform_create(self, serializer):
        if getattr(getattr(self.request.user, "profile", None), "role", None) != "student":
            raise PermissionDenied("Only students can post status updates.")
        serializer.save(user=self.request.user)


@api_view(["GET"])
@permission_classes([IsTeacher])
@extend_schema(tags=["Search"])
def search_users(request):
    """Teacher-only search for users by username or email (partial, case-insensitive)."""
    q = request.query_params.get("q", "").strip()
    qs = User.objects.select_related("profile").none()
    if q:
        qs = (
            User.objects.select_related("profile")
            .filter(Q(username__icontains=q) | Q(email__icontains=q))
            .order_by("username")[:50]
        )
    data = UserSerializer(qs, many=True).data
    return Response({"count": len(data), "results": data})
