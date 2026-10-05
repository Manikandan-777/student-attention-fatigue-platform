"""JWT Authentication Utilities — Phase 14.

Implements APP-2/3, CON §3:
- Password hashing (bcrypt via passlib).
- JWT token creation and verification (python-jose, HS256).
- FastAPI dependency: get_current_user (validates Bearer token).
- FastAPI dependency: require_role (enforces teacher/admin roles).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import PyJWTError as JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.db.database import get_db
from app.db.models import User

# ---------------------------------------------------------------------------
# Password hashing & policy
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COMMON_PASSWORDS = {
    "password1234",
    "password12345",
    "123456789012",
    "admin12345678",
    "qwerty123456",
    "welcome123456",
    "letmein123456",
}


def validate_password_strength(plain: str) -> None:
    """Validate password according to PW3 policy (min length 12+, no common passwords)."""
    if not plain or len(plain) < 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WEAK_PASSWORD", "message": "Password must be at least 12 characters long."},
        )
    if plain.lower() in COMMON_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WEAK_PASSWORD", "message": "Password is too common or easily guessable."},
        )


def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain-text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT creation, verification & server-side revocation (SM1)
# ---------------------------------------------------------------------------

_revoked_tokens: set[str] = set()


def revoke_token(token: str) -> None:
    """Add a token to the server-side revocation deny-list (SM1)."""
    if token:
        _revoked_tokens.add(token)


def is_token_revoked(token: str) -> bool:
    """Check if token has been explicitly revoked."""
    return token in _revoked_tokens


def clear_revoked_tokens() -> None:
    """Clear revocation list (for test session reset)."""
    _revoked_tokens.clear()


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT with sub=username and role claim (SM8: minimal claims)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT. Raises JWTError on invalid/expired/revoked token."""
    if is_token_revoked(token):
        raise JWTError("Token has been revoked.")
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "UNAUTHENTICATED", "message": "Invalid or missing authentication token."},
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    token: Optional[str] = Query(None),
    db: DBSession = Depends(get_db),
) -> User:
    """Dependency: decode JWT, load User from DB. Raises 401 on any failure."""
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise _CREDENTIALS_EXCEPTION
    try:
        payload = decode_access_token(raw_token)
        username: str = payload.get("sub", "")
        if not username:
            raise _CREDENTIALS_EXCEPTION
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    user = db.query(User).filter(User.username == username, User.active == True).first()
    if user is None:
        raise _CREDENTIALS_EXCEPTION
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: require role=admin. Raises 403 otherwise."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin role required."},
        )
    return current_user


def require_teacher_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: require role=teacher or admin. Raises 403 otherwise."""
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Teacher or admin role required."},
        )
    return current_user


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: require role=teacher ONLY. Admins receive 403 (teacher-exclusive endpoint)."""
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Teacher role required."},
        )
    return current_user

