"""
Input validation & sanitization helpers.
All public functions raise ValueError on bad input.
"""
import re
import bleach


_UUID_RE  = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)
_UUID_IN_TEXT = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r'^\+?[\d\s\-().]{7,20}$')
_NAME_RE  = re.compile(r"^[A-Za-z\s'.,-]{2,100}$")


def clean(value: str, max_len: int = 255) -> str:
    """Strip HTML/JS and extra whitespace from a string."""
    if not isinstance(value, str):
        raise ValueError("Expected a string value.")
    cleaned = bleach.clean(value.strip(), tags=[], strip=True)
    if len(cleaned) > max_len:
        raise ValueError(f"Value exceeds maximum length of {max_len} characters.")
    return cleaned


def validate_name(value: str) -> str:
    val = clean(value, 100)
    if not _NAME_RE.match(val):
        raise ValueError("Name contains invalid characters.")
    return val


def validate_phone(value: str) -> str:
    val = clean(value, 20)
    if not _PHONE_RE.match(val):
        raise ValueError("Invalid phone number format.")
    return val


def validate_role(value: str, valid: set) -> str:
    val = clean(value, 50)
    if val not in valid:
        raise ValueError(f"Role must be one of: {', '.join(sorted(valid))}.")
    return val


def validate_text(value: str, max_len: int = 255) -> str:
    """Generic text field — just sanitize."""
    return clean(value, max_len)


def extract_uuid(raw: str) -> str:
    """
    Parse a QR payload and return the bare UUID string.
    Handles: plain UUID, URL containing UUID, or UUID with surrounding whitespace.
    Raises ValueError if no valid UUID found.
    """
    if not isinstance(raw, str):
        raise ValueError("QR payload must be a string.")
    stripped = raw.strip()

    # Direct UUID match
    if _UUID_RE.match(stripped):
        return stripped.lower()

    # UUID embedded in a URL or other text
    match = _UUID_IN_TEXT.search(stripped)
    if match:
        return match.group().lower()

    raise ValueError("No valid UUID found in QR payload.")
