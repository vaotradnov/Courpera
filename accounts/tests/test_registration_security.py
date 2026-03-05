from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.forms import RegistrationForm
from accounts.validators import PasswordComplexityValidator

User = get_user_model()


@pytest.mark.django_db
def test_password_complexity_validator():
    v = PasswordComplexityValidator()
    # Too weak
    with pytest.raises(ValidationError):
        v.validate("password")
    with pytest.raises(ValidationError):
        v.validate("Password")
    with pytest.raises(ValidationError):
        v.validate("Password1")
    # Strong enough
    v.validate("Strong#Passw0rd")


@pytest.mark.django_db
def test_registration_duplicate_checks():
    User.objects.create_user(username="demo", email="dup@example.com", password="Strong#Passw0rd")
    data = {
        "username": "Demo",  # case-insensitive collision
        "email": "dup@example.com",
        "role": "student",
        "password1": "Strong#Passw0rd",
        "password2": "Strong#Passw0rd",
    }
    form = RegistrationForm(data)
    assert not form.is_valid()
    assert "email" in form.errors or "username" in form.errors
