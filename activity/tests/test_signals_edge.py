from __future__ import annotations

from activity.signals import notify_enrolment, notify_material


def test_notify_enrolment_noop_when_not_created(db, make_course, student_user):
    course = make_course()
    enrol = course.enrolments.create(student=student_user)
    # Call with created=False; should return early without error
    notify_enrolment(sender=type(enrol), instance=enrol, created=False)


def test_notify_material_noop_when_not_created(db, make_course, teacher_user):
    from materials.models import Material

    course = make_course()
    # Unsaved instance is fine for this edge test; the handler only reads fields
    m = Material(course=course, title="t", uploaded_by=teacher_user)
    notify_material(sender=Material, instance=m, created=False)
