import re
import time


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def truncate_string(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def debounce(delay_seconds: float):
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
