from __future__ import annotations

from typing import List

from .models import Course


DEFAULT_SUBJECTS: List[str] = [
    "Data Science",
    "Computer Science",
    "Business",
    "Personal Development",
    "Language Learning",
]


def course_subjects(request) -> dict:
    try:
        qs = (
            Course.objects.exclude(subject="")
            .values_list("subject", flat=True)
            .distinct()
            .order_by("subject")
        )
        subjects = list(qs)
    except Exception:
        subjects = []
    # Seed with defaults when empty; merge unique
    seen = set()
    merged: List[str] = []
    for s in subjects + DEFAULT_SUBJECTS:
        if not s:
            continue
        if s not in seen:
            merged.append(s)
            seen.add(s)
    return {"course_subjects": merged}

