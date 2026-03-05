from __future__ import annotations

import random
import string

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def _make(min_len=12, have_upper=True, have_lower=True, have_digit=True, have_symbol=True):
    parts = []
    if have_upper:
        parts.append(random.choice(string.ascii_uppercase))
    if have_lower:
        parts.append(random.choice(string.ascii_lowercase))
    if have_digit:
        parts.append(random.choice(string.digits))
    if have_symbol:
        parts.append(random.choice("!@#$%^&*()-_=+[]{};:,.?/"))
    # Allowed padding alphabet respects the requested missing classes
    alphabet = ""
    if have_upper:
        alphabet += string.ascii_uppercase
    if have_lower:
        alphabet += string.ascii_lowercase
    if have_digit:
        alphabet += string.digits
    if have_symbol:
        alphabet += "!@#$%^&*()-_=+[]{};:,.?/"
    # Ensure alphabet not empty (fallback)
    if not alphabet:
        alphabet = string.ascii_lowercase
    # pad to length without introducing excluded classes
    while len(parts) < min_len:
        parts.append(random.choice(alphabet))
    random.shuffle(parts)
    return "".join(parts)


@pytest.mark.django_db
def test_password_property_samples_cover_missing_classes():
    # randomised samples for missing classes should fail
    cases = [
        dict(have_upper=False),
        dict(have_lower=False),
        dict(have_digit=False),
        dict(have_symbol=False),
    ]
    for params in cases:
        for _ in range(5):
            pwd = _make(**params)
            with pytest.raises(ValidationError):
                validate_password(pwd)

    # a valid mix should pass
    for _ in range(5):
        validate_password(_make())
