from __future__ import annotations

import csv
from typing import Dict, Iterable

from django.http import HttpResponse

from assignments.models import Assignment, Grade
from assignments.utils import compute_course_percentage

from .models import Course, Enrolment


def build_grade_rows(
    course: Course, assignments: Iterable[Assignment]
) -> Dict[int, Dict[int, Grade]]:
    """Return a nested mapping of student_id -> assignment_id -> Grade.

    Only rows for the given course and assignments are included.
    """
    qs = Grade.objects.filter(course=course, assignment__in=list(assignments)).select_related(
        "student", "assignment"
    )
    rows: Dict[int, Dict[int, Grade]] = {}
    for g in qs:
        row = rows.setdefault(g.student_id, {})
        row[g.assignment_id] = g
    return rows


def _format_marks(g: Grade) -> str:
    ach = int(g.achieved_marks) if float(g.achieved_marks or 0).is_integer() else g.achieved_marks
    mx = int(g.max_marks) if float(g.max_marks or 0).is_integer() else g.max_marks
    return f"{ach}/{mx}"


def gradebook_csv_response(course: Course) -> HttpResponse:
    """Build a CSV export for the teacher gradebook for a course.

    Columns: username, S-ID, each assignment ("X/Y"), and course percentage.
    """
    assignments = list(
        Assignment.objects.filter(course=course, is_published=True).order_by("title")
    )
    enrolments = list(
        Enrolment.objects.filter(course=course)
        .select_related("student", "student__profile")
        .order_by("student__username")
    )
    rows = build_grade_rows(course, assignments)

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f"attachment; filename=gradebook_course_{course.id}.csv"
    writer = csv.writer(resp)
    header = ["username", "S-ID"] + [a.title for a in assignments] + ["course %"]
    writer.writerow(header)
    for e in enrolments:
        sid = getattr(getattr(e.student, "profile", None), "student_number", None)
        sid_val = sid if sid else f"S{e.student.id:07d}"
        row: list[str] = [e.student.username, sid_val]
        for a in assignments:
            g = rows.get(e.student_id, {}).get(a.id)
            row.append(_format_marks(g) if g else "")
        pct = compute_course_percentage(course, e.student)
        row.append(f"{pct:.2f}")
        writer.writerow(row)
    return resp
