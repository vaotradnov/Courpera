from __future__ import annotations

from typing import Any, cast

from django import forms
from django.utils import timezone

from .models import Assignment, AssignmentType, QuizAnswerChoice, QuizQuestion


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = (
            "type",
            "title",
            "instructions",
            "available_from",
            "deadline",
            "attempts_allowed",
            "max_marks",
            "attempts_policy",
        )
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 4}),
            # Use a local datetime input for better UX (browser-native picker)
            "deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "available_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure only the defined types are selectable and set a sensible default
        from .models import AssignmentType as _AT

        cast(forms.ChoiceField, self.fields["type"]).choices = list(_AT.choices)
        if not self.initial.get("type"):
            self.fields["type"].initial = _AT.QUIZ
        # Set attempts_policy initial based on type (quiz -> Best; else Latest)
        try:
            atype = (
                (self.data.get("type") if hasattr(self, "data") and self.data else None)
                or self.initial.get("type")
                or getattr(self.instance, "type", None)
            )
            if atype == AssignmentType.QUIZ:
                self.fields["attempts_policy"].initial = Assignment.AttemptsPolicy.BEST
            elif atype:
                self.fields["attempts_policy"].initial = Assignment.AttemptsPolicy.LATEST
        except Exception:
            pass

        # For create form, avoid strict client-side min to prevent browser prompts;
        # server-side validation enforces correctness.
        # Ensure initial deadline renders in the widget format if present
        if self.instance and self.instance.deadline:
            d = self.instance.deadline
            if timezone.is_aware(d):
                d = timezone.localtime(d, timezone.get_current_timezone())
            self.fields["deadline"].initial = d.strftime("%Y-%m-%dT%H:%M")
        if self.instance and getattr(self.instance, "available_from", None):
            a = self.instance.available_from
            if timezone.is_aware(a):
                a = timezone.localtime(a, timezone.get_current_timezone())
            self.fields["available_from"].initial = a.strftime("%Y-%m-%dT%H:%M")

    def clean_deadline(self):
        d = self.cleaned_data.get("deadline")
        # Allow empty; if present, convert to aware and enforce future
        if not d:
            return d
        if timezone.is_naive(d):
            d = timezone.make_aware(d, timezone.get_current_timezone())
        if d <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")
        return d

    def clean_available_from(self):
        a = self.cleaned_data.get("available_from")
        if not a:
            return a
        if timezone.is_naive(a):
            a = timezone.make_aware(a, timezone.get_current_timezone())
        return a

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        a = cleaned.get("available_from")
        d = cleaned.get("deadline")
        if a and d and a >= d:
            self.add_error("available_from", "Availability must be before the deadline.")
        return cleaned

    def clean_attempts_allowed(self):
        val = self.cleaned_data.get("attempts_allowed")
        try:
            val = int(val or 0)
        except Exception:
            raise forms.ValidationError("Invalid attempts value.")
        if val < 1:
            raise forms.ValidationError("Attempts must be at least 1.")
        # If editing an existing assignment, prevent lowering below used attempts
        if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
            try:
                from .models import Attempt  # local import to avoid cycles

                used = Attempt.objects.filter(assignment=self.instance).count()
                if val < used:
                    raise forms.ValidationError(
                        f"Cannot set attempts below attempts already used ({used})."
                    )
            except Exception:
                pass
        return val

    def clean_max_marks(self):
        mm = self.cleaned_data.get("max_marks")
        # Allow omission to keep current or default value
        if mm in (None, ""):
            if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
                return getattr(self.instance, "max_marks", 100.0)
            return 100.0
        try:
            mm_val = cast(float | int | str, mm)
            mm = float(mm_val)
        except Exception:
            raise forms.ValidationError("Invalid maximum marks.")
        if mm <= 0:
            raise forms.ValidationError("Maximum marks must be greater than zero.")
        return mm


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ("text",)
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 2, "class": "w-100", "placeholder": "Question text"}
            )
        }


class QuizAnswerChoiceForm(forms.ModelForm):
    class Meta:
        model = QuizAnswerChoice
        fields = ("text", "is_correct", "explanation")
        widgets = {
            "text": forms.TextInput(attrs={"class": "input w-100", "placeholder": "Answer text"}),
            "explanation": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "w-100 no-resize",
                    "placeholder": "Optional; shown in feedback after attempt",
                }
            ),
        }


class AssignmentMetaForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = (
            "title",
            "instructions",
            "available_from",
            "deadline",
            "attempts_allowed",
            "max_marks",
            "attempts_policy",
        )
        widgets = {
            "deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "available_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "instructions": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.deadline:
            d = self.instance.deadline
            if timezone.is_aware(d):
                d = timezone.localtime(d, timezone.get_current_timezone())
            self.fields["deadline"].initial = d.strftime("%Y-%m-%dT%H:%M")
        if self.instance and getattr(self.instance, "available_from", None):
            a = self.instance.available_from
            if timezone.is_aware(a):
                a = timezone.localtime(a, timezone.get_current_timezone())
            self.fields["available_from"].initial = a.strftime("%Y-%m-%dT%H:%M")
        # Add client-side min attribute to inputs (current local time)
        try:
            now = timezone.localtime(timezone.now(), timezone.get_current_timezone())
            now_str = now.strftime("%Y-%m-%dT%H:%M")
            if "available_from" in self.fields:
                self.fields["available_from"].widget.attrs.setdefault("min", now_str)
            if "deadline" in self.fields:
                self.fields["deadline"].widget.attrs.setdefault("min", now_str)
            # Set attempts_policy initial based on current type if empty
            if not self.fields["attempts_policy"].initial:
                atype = (
                    self.data.get("type") if hasattr(self, "data") and self.data else None
                ) or getattr(self.instance, "type", None)
                if atype == AssignmentType.QUIZ:
                    self.fields["attempts_policy"].initial = Assignment.AttemptsPolicy.BEST
                elif atype:
                    self.fields["attempts_policy"].initial = Assignment.AttemptsPolicy.LATEST
        except Exception:
            pass

    def clean_deadline(self):
        d = self.cleaned_data.get("deadline")
        if not d:
            return d
        if timezone.is_naive(d):
            d = timezone.make_aware(d, timezone.get_current_timezone())
        if d <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")
        return d

    def clean_available_from(self):
        a = self.cleaned_data.get("available_from")
        if not a:
            return a
        if timezone.is_naive(a):
            a = timezone.make_aware(a, timezone.get_current_timezone())
        return a

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        a = cleaned.get("available_from")
        d = cleaned.get("deadline")
        if a and d and a >= d:
            self.add_error("available_from", "Availability must be before the deadline.")
        return cleaned

    def clean_attempts_allowed(self):
        val = self.cleaned_data.get("attempts_allowed")
        try:
            val = int(val or 0)
        except Exception:
            raise forms.ValidationError("Invalid attempts value.")
        if val < 1:
            raise forms.ValidationError("Attempts must be at least 1.")
        if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
            try:
                from .models import Attempt

                used = Attempt.objects.filter(assignment=self.instance).count()
                if val < used:
                    raise forms.ValidationError(
                        f"Cannot set attempts below attempts already used ({used})."
                    )
            except Exception:
                pass
        return val

    def clean_max_marks(self):
        mm = self.cleaned_data.get("max_marks")
        if mm in (None, ""):
            if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
                return getattr(self.instance, "max_marks", 100.0)
            return 100.0
        try:
            mm_val = cast(float | int | str, mm)
            mm = float(mm_val)
        except Exception:
            raise forms.ValidationError("Invalid maximum marks.")
        if mm <= 0:
            raise forms.ValidationError("Maximum marks must be greater than zero.")
        return mm


class GradeAttemptForm(forms.Form):
    marks_awarded = forms.FloatField(min_value=0.0)
    feedback_text = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    override_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
