"""
MARTIQ - Input Validators
----------------------------
Small, dependency-free validation helpers shared across pages.
Kept separate from database.py because these check raw form input
before it ever touches SQL - no database access happens here.
"""

import re

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_non_empty(value: str) -> bool:
    return bool(value and value.strip())


def is_valid_phone(phone: str) -> bool:
    """Accepts 10-13 digit phone numbers, ignoring spaces/+/-/() formatting."""
    if not phone:
        return False
    digits_only = re.sub(r"[^0-9]", "", phone)
    return 10 <= len(digits_only) <= 13


def is_valid_email(email: str) -> bool:
    """Empty email is allowed (it's optional); non-empty must look valid."""
    if not email or not email.strip():
        return True
    return bool(_EMAIL_PATTERN.match(email.strip()))


def validate_customer_form(name: str, phone: str, email: str) -> list:
    """Return a list of human-readable error strings (empty list = valid)."""
    errors = []
    if not is_non_empty(name):
        errors.append("Name is required.")
    if not is_non_empty(phone):
        errors.append("Phone number is required.")
    elif not is_valid_phone(phone):
        errors.append("Phone number must be 10–13 digits.")
    if not is_valid_email(email):
        errors.append("Email address format looks invalid.")
    return errors
