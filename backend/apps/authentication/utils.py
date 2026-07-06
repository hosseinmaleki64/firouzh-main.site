import re


def normalize_phone(phone: str) -> str:
    """
    Convert Iranian phone numbers to international format.

    Examples:
        09141234567     -> +989141234567
        989141234567    -> +989141234567
        +989141234567   -> +989141234567
    """

    phone = phone.strip()
    phone = re.sub(r"\s+", "", phone)

    if phone.startswith("+98"):
        return phone

    if phone.startswith("98"):
        return "+" + phone

    if phone.startswith("0"):
        return "+98" + phone[1:]

    raise ValueError("Invalid phone number format.")