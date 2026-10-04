"""Auth package."""
from app.auth.router import router
from app.auth.jwt import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
    require_admin,
    require_teacher_or_admin,
)

__all__ = [
    "router",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_admin",
    "require_teacher_or_admin",
]
