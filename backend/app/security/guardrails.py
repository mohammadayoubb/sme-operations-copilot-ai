import re

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"forget everything",
    r"you are now",
    r"new persona",
    r"system prompt",
    r"reveal your instructions",
    r"disregard.*instructions",
    r"act as (?!a business)",
    r"jailbreak",
]

_PHONE_RE = re.compile(r"\+?[\d\s\-\(\)]{7,15}")
_EMAIL_RE = re.compile(r"[\w\.\-]+@[\w\.\-]+\.\w+")


def redact_pii(text: str) -> str:
    text = _PHONE_RE.sub("[PHONE REDACTED]", text)
    text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
    return text


def detect_injection(text: str) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in _INJECTION_PATTERNS)


def is_safe_input(text: str) -> tuple[bool, str | None]:
    """Returns (is_safe, reason). Use before passing any user input to an LLM."""
    if detect_injection(text):
        return False, "Potential prompt injection detected."
    return True, None
