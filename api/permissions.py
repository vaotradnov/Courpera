"""Custom permissions for REST API v1."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthenticatedOrReadOnly(BasePermission):
    def has_permission(self, request, view):  # noqa: D401
        return bool(
            request.method in SAFE_METHODS or (request.user and request.user.is_authenticated)
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(profile, "role", None) == "teacher"
        )


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, "profile", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(profile, "role", None) == "student"
        )
