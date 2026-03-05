"""Forms for course feedback."""

from __future__ import annotations

from django import forms

from .models_feedback import Feedback


class FeedbackForm(forms.ModelForm):
    rating = forms.ChoiceField(choices=[(i, i) for i in range(1, 6)], label="Rating")

    class Meta:
        model = Feedback
        fields = ("rating", "comment", "anonymous")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        }
