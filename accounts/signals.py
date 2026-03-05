"""Signals for automatic profile management.

On user creation, create a default `UserProfile` with the student role.
This keeps registration straightforward while still supporting a role
selection UI that updates the profile after creation.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Role, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs):  # noqa: D401
    """Create a profile for new users (default role: student)."""
    if created:
        # Default to student role; assign a deterministic student number
        # derived from the user id for uniqueness and simplicity.
        sn = f"S{instance.id:07d}"
        UserProfile.objects.create(user=instance, role=Role.STUDENT, student_number=sn)


@receiver(pre_save, sender=UserProfile)
def ensure_student_number(sender, instance: UserProfile, **kwargs):  # noqa: D401
    """Ensure students always have a student_number assigned.

    If a profile transitions to the student role and the number is empty,
    assign a deterministic value based on the user id.
    """
    if getattr(instance, "role", None) == Role.STUDENT and not getattr(
        instance, "student_number", ""
    ):  # type: ignore[attr-defined]
        if getattr(instance, "user_id", None):
            instance.student_number = f"S{instance.user_id:07d}"


@receiver(pre_save, sender=UserProfile)
def ensure_instructor_id(sender, instance: UserProfile, **kwargs):  # noqa: D401
    """Ensure teachers have an instructor_id (I-prefixed unique ID)."""
    if getattr(instance, "role", None) == Role.TEACHER and not getattr(
        instance, "instructor_id", None
    ):  # type: ignore[attr-defined]
        if getattr(instance, "user_id", None):
            instance.instructor_id = f"I{instance.user_id:07d}"
