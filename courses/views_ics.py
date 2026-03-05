"""ICS export for courses (Stage 7).

Generates a basic iCalendar file with one event per material upload.
This avoids adding a dedicated events model while still demonstrating
ICS generation and consumption.
"""

from __future__ import annotations

from datetime import datetime, timezone

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Course


def _ical_escape(s: str) -> str:
    # Use raw backslash escapes to avoid Python SyntaxWarning on unknown escapes.
    return s.replace(",", r"\, ").replace(";", r"\; ").replace("\n", "\\n")


def course_calendar(request: HttpRequest, pk: int) -> HttpResponse:
    course = get_object_or_404(Course, pk=pk)
    now = datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Courpera//Course Calendar//EN",
        f"X-WR-CALNAME:{_ical_escape(course.title)}",
    ]
    # Use materials as dated items; keep minimal fields for compatibility
    for m in course.materials.all():
        uid = f"material-{m.pk}@courpera"
        dtstamp = now.strftime("%Y%m%dT%H%M%SZ")
        dtstart = m.created_at.strftime("%Y%m%dT%H%M%SZ")
        summary = _ical_escape(f"{course.title}: {m.title}")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    resp = HttpResponse(body, content_type="text/calendar")
    resp["Content-Disposition"] = f"attachment; filename=course-{course.pk}.ics"
    return resp
