import re

from django.core.exceptions import ValidationError

def validate_iranian_phone(phone: str):
    pattern = r"^\+989\d{9}$"

    if not re.match(pattern, phone):
        raise ValueError("Invalid Iranian phone number.")