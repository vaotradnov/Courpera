"""Serializers for REST API v1 (Stage 8).

Keep responses modest and role-aware. File uploads occur via HTML forms;
the API exposes metadata for materials and download URLs where allowed.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from activity.models import Status
from courses.models import Course, Enrolment
from courses.models_feedback import Feedback
from materials.models import Material

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "role")

    def get_role(self, obj) -> str | None:
        profile = getattr(obj, "profile", None)
        return getattr(profile, "role", None)


class CourseSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Course
        fields = ("id", "title", "description", "owner", "created_at", "updated_at")
        read_only_fields = ("owner", "created_at", "updated_at")


class EnrolmentSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    student = UserSerializer(read_only=True)

    class Meta:
        model = Enrolment
        fields = ("id", "course", "student", "completed", "created_at")
        read_only_fields = ("student", "created_at")


class MaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ("id", "course", "title", "size_bytes", "mime", "created_at", "file_url")
        read_only_fields = ("created_at", "size_bytes", "mime", "file_url")

    def get_file_url(self, obj) -> str:
        request = self.context.get("request")
        try:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        except Exception:
            return ""


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("id", "course", "student", "rating", "comment", "anonymous", "created_at")
        read_only_fields = ("student", "created_at")


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("id", "text", "created_at")
        read_only_fields = ("created_at",)
