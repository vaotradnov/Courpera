from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Enrolment
from materials.models import Material

from .models import Notification


@receiver(post_save, sender=Enrolment)
def notify_enrolment(sender, instance: Enrolment, created: bool, **kwargs):
    if not created:
        return
    # Notify teacher (course owner) about the new enrolment
    course = instance.course
    teacher = course.owner
    student = instance.student
    Notification.objects.create(
        user=teacher,
        actor=student,
        type=Notification.TYPE_ENROLMENT,
        course=course,
        message=f"New enrolment: {student.username} in {course.title}",
    )


@receiver(post_save, sender=Material)
def notify_material(sender, instance: Material, created: bool, **kwargs):
    if not created:
        return
    # Notify enrolled students of new material
    course = instance.course
    # Avoid notifying the uploader if they are also enrolled (teacher not likely enrolled)
    student_ids = list(course.enrolments.values_list("student_id", flat=True))
    if not student_ids:
        return
    # Bulk create notifications
    to_create = []
    for sid in student_ids:
        to_create.append(
            Notification(
                user_id=sid,
                actor=instance.uploaded_by,
                type=Notification.TYPE_MATERIAL,
                course=course,
                message=f"New material in {course.title}: {instance.title}",
            )
        )
    Notification.objects.bulk_create(to_create)
