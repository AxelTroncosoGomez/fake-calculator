import re
import time


def validate_email(email: str) -> bool:
    """Check whether a string is a valid email address.

    Args:
        email: The email string to validate.

    Returns:
        True if the email matches the expected format, False otherwise.
    """
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def truncate_string(text: str, max_length: int) -> str:
    """Truncate a string to a maximum length with an ellipsis suffix.

    Args:
        text: The input string.
        max_length: The maximum allowed length.

    Returns:
        The original string if within the limit, or a truncated string
        ending with "..." otherwise.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def debounce(delay_seconds: float):
    """Create a debounced version of a function.

    Args:
        delay_seconds: Minimum interval in seconds between calls.

    Returns:
        A decorator that wraps a function so it ignores calls made
        within delay_seconds of the previous invocation.
    """

    def decorator(fn):
        last_called = 0.0

        def wrapper(*args, **kwargs):
            nonlocal last_called
            now = time.time()
            if now - last_called >= delay_seconds:
                last_called = now
                return fn(*args, **kwargs)
            return None

        return wrapper

    return decorator
