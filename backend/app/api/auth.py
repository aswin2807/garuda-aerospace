import hashlib
import secrets
import logging
import time
from collections import defaultdict
from datetime import timedelta, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import (
    User,
    PasswordReset,
    RevokedToken,
    get_utc_now,
)
from backend.app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    RegisterResponse,
    Token,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyResetTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    LogoutResponse,
)
from backend.app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.app.services.email_service import email_service

logger = logging.getLogger("garuda.auth")

SESSION_COOKIE_NAME = "garuda_session"
REMEMBER_ME_DAYS = 7
DEFAULT_SESSION_HOURS = 12

# Rate limiting stores (key -> list of request timestamps)
_recovery_rate_limits: Dict[str, List[float]] = defaultdict(list)
RECOVERY_RATE_LIMIT_WINDOW_SEC = 60.0
RECOVERY_RATE_LIMIT_MAX_REQUESTS = 5

_login_rate_limits: Dict[str, List[float]] = defaultdict(list)
LOGIN_RATE_LIMIT_WINDOW_SEC = 60.0
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10


def reset_rate_limits() -> None:
    """Clear in-memory rate limit counters (used by test suites)."""
    _recovery_rate_limits.clear()
    _login_rate_limits.clear()


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def is_expired(dt) -> bool:
    if dt is None:
        return True
    now = get_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < now


def _extract_token(request: Request, bearer_token: Optional[str] = None) -> Optional[str]:
    if bearer_token:
        return bearer_token.strip()
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip()
    return None


def verify_session_token(raw_token: str, db: Session) -> Optional[User]:
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    revoked = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
    if revoked:
        return None

    payload = decode_access_token(raw_token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user or user.account_status == "DISABLED":
        return None

    # Check if session was issued before the user's last password reset / session invalidation
    if user.session_invalidated_at is not None:
        inv_dt = (
            user.session_invalidated_at.replace(tzinfo=timezone.utc)
            if user.session_invalidated_at.tzinfo is None
            else user.session_invalidated_at
        )
        inv_ms = int(inv_dt.timestamp() * 1000)
        token_iat_ms = payload.get("iat_ms")
        if token_iat_ms is not None:
            if int(token_iat_ms) <= inv_ms:
                return None
        else:
            token_iat = payload.get("iat")
            if token_iat is not None and int(token_iat) <= int(inv_dt.timestamp()):
                return None

    return user


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    resolved_token = _extract_token(request, token)
    if not resolved_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_session_token(resolved_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    now = get_utc_now()
    # Self-registration creates an immediately active OPERATOR account without email verification
    user = User(
        email=user_in.email,
        name=user_in.name,
        role="OPERATOR",
        password_hash=get_password_hash(user_in.password),
        is_active=True,
        is_email_verified=True,
        account_status="ACTIVE",
        last_login_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    expires_delta = timedelta(days=REMEMBER_ME_DAYS)
    access_token = create_access_token(subject=user.id, expires_delta=expires_delta)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
        max_age=REMEMBER_ME_DAYS * 24 * 3600,
        path="/",
    )

    return RegisterResponse(
        success=True,
        message="Account created successfully.",
        requires_verification=False,
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, response: Response, db: Session = Depends(get_db)):
    now_ts = time.time()
    recent_failures = [
        ts for ts in _login_rate_limits[user_in.email] if now_ts - ts < LOGIN_RATE_LIMIT_WINDOW_SEC
    ]
    if len(recent_failures) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait a minute before trying again.",
        )

    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        recent_failures.append(now_ts)
        _login_rate_limits[user_in.email] = recent_failures
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not user.is_active or user.account_status == "DISABLED":
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Ensure any legacy account is marked active and verified without blocking login
    if not user.is_email_verified or user.account_status == "PENDING_VERIFICATION":
        user.is_email_verified = True
        user.account_status = "ACTIVE"

    # Clear failed login counter on success
    _login_rate_limits.pop(user_in.email, None)

    user.last_login_at = get_utc_now()
    db.commit()
    db.refresh(user)

    expires_delta = (
        timedelta(days=REMEMBER_ME_DAYS)
        if user_in.remember_me
        else timedelta(hours=DEFAULT_SESSION_HOURS)
    )
    access_token = create_access_token(subject=user.id, expires_delta=expires_delta)

    max_age = REMEMBER_ME_DAYS * 24 * 3600 if user_in.remember_me else None
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
        max_age=max_age,
        path="/",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    now_ts = time.time()
    recent_attempts = [
        ts for ts in _recovery_rate_limits[req.email] if now_ts - ts < RECOVERY_RATE_LIMIT_WINDOW_SEC
    ]
    if len(recent_attempts) >= RECOVERY_RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password recovery requests. Please wait a minute before trying again.",
        )
    recent_attempts.append(now_ts)
    _recovery_rate_limits[req.email] = recent_attempts

    generic_message = (
        "We've received your request. If an account exists for this email address, "
        "you'll receive a password reset link shortly."
    )
    user = db.query(User).filter(User.email == req.email, User.is_active.is_(True)).first()

    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = get_utc_now() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

        # Invalidate any previously unconsumed tokens for this user
        db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.used_at.is_(None),
        ).update({"used_at": get_utc_now()})

        reset_entry = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_entry)
        db.commit()

        delivery = email_service.send_password_reset_email(
            to_email=user.email,
            full_name=user.name,
            raw_token=raw_token,
        )
        logger.info(
            "Password reset email processed: user_id=%s sent=%s provider=%s",
            user.id,
            delivery.sent,
            delivery.provider,
        )

    return ForgotPasswordResponse(message=generic_message)


@router.get("/verify-reset-token", response_model=VerifyResetTokenResponse)
def verify_reset_token(token: str = Query(...), db: Session = Depends(get_db)):
    token_str = token.strip()
    if not token_str:
        return VerifyResetTokenResponse(valid=False, message="Token is required.")

    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    record = db.query(PasswordReset).filter(PasswordReset.token_hash == token_hash).first()

    if not record or record.used_at is not None or is_expired(record.expires_at):
        return VerifyResetTokenResponse(
            valid=False,
            message="This password reset link is invalid, expired, or has already been used.",
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    return VerifyResetTokenResponse(
        valid=True,
        email=user.email if user else None,
        message="Token is valid.",
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not req.new_password:
        raise HTTPException(status_code=400, detail="Password is required.")

    if len(req.new_password.encode("utf-8")) > settings.MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password cannot exceed {settings.MAX_PASSWORD_BYTES} bytes in UTF-8 encoding.",
        )

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    token_str = req.token.strip()
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    record = db.query(PasswordReset).filter(PasswordReset.token_hash == token_hash).first()

    if not record or record.used_at is not None or is_expired(record.expires_at):
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid, expired, or has already been used.",
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User account is invalid or disabled.")

    now = get_utc_now()
    user.password_hash = get_password_hash(req.new_password)
    user.session_invalidated_at = now
    record.used_at = now

    # Also invalidate any other unconsumed reset tokens for this user
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used_at.is_(None),
    ).update({"used_at": now})

    db.commit()

    # Send password change notification email
    delivery = email_service.send_password_changed_email(
        to_email=user.email,
        full_name=user.name,
    )
    logger.info(
        "Password reset completed and sessions invalidated: user_id=%s notify_sent=%s",
        user.id,
        delivery.sent,
    )

    return ResetPasswordResponse(
        success=True,
        message="Your password has been successfully reset. You may now sign in with your new password.",
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    resolved_token = _extract_token(request, token)
    if resolved_token:
        token_hash = hashlib.sha256(resolved_token.encode("utf-8")).hexdigest()
        existing = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
        if not existing:
            db.add(RevokedToken(token_hash=token_hash))
            db.commit()

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return LogoutResponse(success=True, message="Successfully logged out.")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
