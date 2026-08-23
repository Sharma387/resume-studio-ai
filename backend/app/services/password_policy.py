"""Password policy enforcement."""

import re
import secrets
import string


class PasswordPolicyError(ValueError):
    pass


_MIN_LENGTH = 12
_UPPERCASE = re.compile(r"[A-Z]")
_LOWERCASE = re.compile(r"[a-z]")
_DIGIT = re.compile(r"[0-9]")
_SPECIAL = re.compile(r"[!@#$%^&*()_\-+=\[\]{}|;:'\",.<>/?`~]")


def validate(password: str) -> None:
    errors: list[str] = []
    if len(password) < _MIN_LENGTH:
        errors.append(f"At least {_MIN_LENGTH} characters required")
    if not _UPPERCASE.search(password):
        errors.append("Must include an uppercase letter")
    if not _LOWERCASE.search(password):
        errors.append("Must include a lowercase letter")
    if not _DIGIT.search(password):
        errors.append("Must include a digit")
    if not _SPECIAL.search(password):
        errors.append("Must include a special character")
    if errors:
        raise PasswordPolicyError("; ".join(errors))


def generate_temporary() -> str:
    """Generate a secure random temporary password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(16))
        try:
            validate(pwd)
            return pwd
        except PasswordPolicyError:
            continue
