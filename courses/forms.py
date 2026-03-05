"""Forms for creating courses."""

from __future__ import annotations

from typing import Any, cast

from django import forms

from .context_processors import DEFAULT_SUBJECTS
from .models import Course


class CourseForm(forms.ModelForm):
    """Teacher-facing form for creating/editing courses."""

    class Meta:
        model = Course
        fields = ("title", "description", "subject", "level", "language", "thumbnail")

    # Aux fields for subject selection + custom option
    subject_choice = forms.ChoiceField(required=False)
    new_subject = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build subject choices from existing + defaults
        try:
            from .models import Course as _Course

            existing = list(
                _Course.objects.exclude(subject="")
                .values_list("subject", flat=True)
                .distinct()
                .order_by("subject")
            )
        except Exception:
            existing = []
        seen = set()
        opts = []
        for s in existing + DEFAULT_SUBJECTS:
            if s and s not in seen:
                opts.append((s, s))
                seen.add(s)
        opts.append(("__other__", "Other (add new)…"))
        cast(forms.ChoiceField, self.fields["subject_choice"]).choices = [
            ("", "Select subject")
        ] + opts

        # Initialise selection
        current = (self.instance.subject or "").strip() if getattr(self, "instance", None) else ""
        if current and current in seen:
            self.fields["subject_choice"].initial = current
        elif current:
            self.fields["subject_choice"].initial = "__other__"
            self.fields["new_subject"].initial = current

        # Place fields in a helpful order for templates using as_p/as_table
        self.order_fields(
            [
                "title",
                "description",
                "subject_choice",
                "new_subject",
                "level",
                "language",
                "thumbnail",
            ]
        )

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        # Resolve subject from either dropdown or new text
        choice = (cleaned.get("subject_choice") or "").strip()
        newval = (cleaned.get("new_subject") or "").strip()
        posted_subject = (cleaned.get("subject") or "").strip()
        subject_val = ""
        if choice and choice != "__other__":
            subject_val = choice
        elif newval:
            subject_val = newval
        elif posted_subject:
            # Backwards compatibility if only 'subject' was posted
            subject_val = posted_subject
        cleaned["subject"] = subject_val
        return cleaned


class SyllabusForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("syllabus", "outcomes")
        widgets = {
            "syllabus": forms.Textarea(attrs={"rows": 8, "placeholder": "One item per line"}),
            "outcomes": forms.Textarea(attrs={"rows": 6, "placeholder": "One outcome per line"}),
        }


class AddStudentForm(forms.Form):
    """Teacher utility form to enrol a student by username, email, or Student ID.

    This keeps the UI simple.
    """

    query = forms.CharField(label="Username, email, or Student ID", max_length=150)
