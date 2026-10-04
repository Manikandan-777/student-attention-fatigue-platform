from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import (
    create_access_token,
    get_current_user,
    revoke_token,
    verify_password,
)
from app.auth.rate_limiter import login_rate_limiter
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class MeResponse(BaseModel):
    id: int
    username: str
    role: str
    active: bool


@router.post("/login", response_model=TokenResponse, summary="Obtain JWT token")
def login(request: Request, body: LoginRequest, db: DBSession = Depends(get_db)) -> TokenResponse:
    """Authenticate with username + password; returns JWT + role with rate limiting (APP-26, PW5)."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_key = f"user:{body.username.strip().lower()}"

    # Enforce APP-26 & PW5 rate limiting (both IP and username)
    is_limited_ip, retry_after_ip = login_rate_limiter.is_rate_limited(client_ip)
    is_limited_user, retry_after_user = login_rate_limiter.is_rate_limited(user_key)

    if is_limited_ip or is_limited_user:
        retry_after = max(retry_after_ip, retry_after_user)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "TOO_MANY_ATTEMPTS",
                "message": "Too many failed login attempts. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    user = db.query(User).filter(User.username == body.username, User.active == True).first()
    if not user or not verify_password(body.password, user.password_hash):
        login_rate_limiter.record_failure(client_ip)
        login_rate_limiter.record_failure(user_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect username or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login clears failure history
    login_rate_limiter.record_success(client_ip)
    login_rate_limiter.record_success(user_key)
    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=MeResponse, summary="Current authenticated user")
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    """Return the authenticated user's profile."""
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        active=current_user.active,
    )


@router.post("/logout", summary="Logout and invalidate JWT token (SM1)")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    current_user: User = Depends(get_current_user),
):
    """Invalidate current bearer token server-side (SM1)."""
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    return {"status": "ok", "message": "Successfully logged out."}
