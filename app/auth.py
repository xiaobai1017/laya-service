import secrets

from fastapi import Header, HTTPException

from .config import get_settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    supplied = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

