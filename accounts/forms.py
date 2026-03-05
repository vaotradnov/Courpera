"""Forms for user registration, login, profile editing, and password reset."""

from __future__ import annotations

from io import BytesIO
from typing import Any, cast

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from .models import Role, UserProfile


class RegistrationForm(UserCreationForm):
    """User registration form with a role selector.

    The role field writes to the related `UserProfile` after the `User`
    instance is created. This avoids having to override the auth user
    model in early stages.
    """

    email = forms.EmailField(required=True)
    timezone = forms.ChoiceField(
        required=False,
        choices=[
            ("Europe/London", "Europe/London"),
            ("America/Edmonton", "America/Edmonton"),
            ("UTC", "UTC"),
        ],
    )
    role = forms.ChoiceField(choices=Role.choices, initial=Role.STUDENT)
    secret_word = forms.CharField(
        required=True,
        min_length=6,
        widget=forms.PasswordInput,
        help_text="Used to restore your password (min 6 characters).",
    )

    class Meta:
        model = User
        fields = ("username", "email", "role", "secret_word", "password1", "password2")

    def save(self, commit: bool = True) -> User:
        user = super().save(commit)
        # Update or create profile role selection
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data.get("role") or Role.STUDENT
        # Save secret word as a hash
        from django.contrib.auth.hashers import make_password

        sw = (self.cleaned_data.get("secret_word") or "").strip()
        profile.secret_word_hash = make_password(sw) if sw else ""
        profile.save(update_fields=["role", "secret_word_hash"])  # explicit for clarity
        return user

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        sw = (cleaned.get("secret_word") or "").strip().lower()
        pw1 = (cleaned.get("password1") or "").strip().lower()
        uname = (cleaned.get("username") or "").strip().lower()
        email = (cleaned.get("email") or "").strip().lower()
        if sw and (sw == pw1 or sw == uname or (email and sw == email)):
            raise forms.ValidationError(
                "Secret word must not equal your password, username, or email."
            )
        return cleaned


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Username or email"

    def clean(self):
        cleaned = super().clean()
        login = self.cleaned_data.get("username") or ""
        if "@" in login:
            from django.contrib.auth import get_user_model

            UserModel = get_user_model()
            user = UserModel.objects.filter(email__iexact=login.strip()).first()
            if user:
                self.cleaned_data["username"] = user.get_username()
        return cleaned


class ProfileForm(forms.ModelForm):
    """Edit profile details, email, and optional avatar upload (no role change)."""

    avatar = forms.ImageField(required=False)
    email = forms.EmailField(required=True)
    current_password = forms.CharField(
        required=True, widget=forms.PasswordInput, help_text="Confirm to change email"
    )

    class Meta:
        model = UserProfile
        fields = ("full_name", "phone", "avatar", "timezone")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["email"].initial = getattr(self.user, "email", "")
        try:
            self.fields["timezone"].initial = getattr(self.instance, "timezone", "Europe/London")
        except Exception:
            pass

    def clean_avatar(self):
        f = self.cleaned_data.get("avatar")
        if not f:
            return f
        if getattr(f, "size", 0) > 2 * 1024 * 1024:  # 2 MB limit for avatars
            raise ValidationError("Avatar must be 2 MB or smaller.")
        ctype = getattr(f, "content_type", "")
        if ctype not in ("image/jpeg", "image/png", "image/webp"):
            raise ValidationError("Avatar must be JPEG, PNG, or WEBP.")
        return f

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        # Validate current password and email uniqueness here so is_valid() handles errors gracefully
        if self.user:
            pwd = cleaned.get("current_password") or ""
            if not self.user.check_password(pwd):
                self.add_error("current_password", "Current password is incorrect.")
            email = (cleaned.get("email") or "").strip().lower()
            if email and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
                self.add_error("email", "This email is already in use.")
        return cleaned

    def save(self, commit: bool = True):
        profile: UserProfile = super().save(commit=False)
        f = self.cleaned_data.get("avatar")
        # Apply email change after validation
        if self.user:
            email = (self.cleaned_data.get("email") or "").strip().lower()
            if email and self.user.email != email:
                self.user.email = email
                if commit:
                    self.user.save(update_fields=["email"])

        if f:
            # Resize to max 256px and save as PNG to normalise (if Pillow available)
            try:
                from PIL import (
                    Image as PILImage,  # lazy import to avoid hard dependency at import time
                )

                img: PILImage.Image = PILImage.open(f)
                img = img.convert("RGBA") if img.mode not in ("RGB", "RGBA") else img
                img.thumbnail((256, 256))
                buf = BytesIO()
                img.save(buf, format="PNG", optimize=True)
                profile.avatar.save(
                    f"avatar_{profile.user_id}.png",
                    ContentFile(buf.getvalue()),
                    save=False,
                )
            except ImportError:
                # If Pillow isn't installed, store the original upload as-is
                profile.avatar = f
            except Exception:
                raise ValidationError("Invalid image file.")
        if commit:
            profile.save()
        return profile


class SecretResetForm(forms.Form):
    identifier = forms.CharField(label="Username or email", max_length=150)
    secret_word = forms.CharField(widget=forms.PasswordInput, min_length=6)
    new_password1 = forms.CharField(widget=forms.PasswordInput)
    new_password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = cast(dict[str, Any], super().clean())
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")
        return cleaned
