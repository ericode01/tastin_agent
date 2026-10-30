import os


def require_env(name: str) -> str:
    """Return the value of an environment variable, or fail with a clear message if it is missing."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
