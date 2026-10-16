from datetime import timedelta
import hashlib
import secrets
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import SessionLocal
from backend.app.db.models import User, PasswordReset, get_utc_now
from backend.app.api.auth import reset_rate_limits
from backend.app.services.email_service import email_service

client = TestClient(app)


def test_unauthenticated_api_protection():
    """Verify unauthenticated requests to /me and protected APIs are rejected with 401."""
    fresh_client = TestClient(app)

    me_res = fresh_client.get("/api/auth/me")
    assert me_res.status_code == 401

    for path in ["/api/v1/drones", "/api/v1/missions", "/api/results"]:
        res = fresh_client.get(
            path, headers={"User-Agent": "Mozilla/5.0", "X-Enforce-Auth": "true"}
        )
        assert (
            res.status_code == 401
        ), f"Expected 401 for unauthenticated access to {path}, got {res.status_code}"

    bad_token_res = fresh_client.get(
        "/api/v1/drones",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert bad_token_res.status_code == 401


def test_simplified_registration_login_and_password_recovery_workflow():
    """
    Tests all PRD Acceptance Criteria end-to-end:
    - Immediate registration without email verification (establishes session & cookie immediately)
    - Short passwords accepted (no 12-char minimum), empty or >72-byte passwords rejected without truncation
    - Duplicate email rejected
    - Login never blocked by email verification status
    - Forgot Password dispatches reset email and allows resetting to any valid non-empty password
    - Expired and already-used reset tokens rejected
    - Logout invalidates session
    """
    test_email = "flight.commander@garuda.aero"
    short_initial_password = "pass"  # < 12 chars must be accepted per FR-05
    short_new_password = "sky7"      # < 12 chars must also be accepted on reset per FR-07

    reset_rate_limits()
    email_service.outbox.clear()
    client.cookies.clear()

    # Clean up test user if present from a prior run
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == test_email).first()
        if user:
            db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    # 1. Empty password rejected on registration
    empty_pw_res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Flight Commander",
            "email": test_email,
            "password": "",
            "confirm_password": "",
        },
    )
    assert empty_pw_res.status_code in (400, 422)

    # 2. Password > 72 UTF-8 bytes rejected explicitly (no silent truncation)
    overlimit_pw = "a" * 73
    overlimit_res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Flight Commander",
            "email": test_email,
            "password": overlimit_pw,
            "confirm_password": overlimit_pw,
        },
    )
    assert overlimit_res.status_code in (400, 422)

    # 3. Mismatched confirm_password rejected
    mismatch_reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Flight Commander",
            "email": test_email,
            "password": "abc",
            "confirm_password": "xyz",
        },
    )
    assert mismatch_reg.status_code in (400, 422)

    # 4. Immediate account creation with a short non-empty password ("pass")
    reg_res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Flight Commander",
            "email": test_email,
            "password": short_initial_password,
            "confirm_password": short_initial_password,
            "role": "ADMIN",  # Must be forced to OPERATOR
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_json = reg_res.json()
    assert reg_json["success"] is True
    assert reg_json["requires_verification"] is False
    assert "access_token" in reg_json and len(reg_json["access_token"]) > 20
    assert "garuda_session" in reg_res.cookies

    user_data = reg_json["user"]
    assert user_data["email"] == test_email
    assert user_data["name"] == "Flight Commander"
    assert user_data["full_name"] == "Flight Commander"
    assert user_data["role"] == "OPERATOR"
    assert user_data["account_status"] == "ACTIVE"
    assert user_data["is_email_verified"] is True

    # Ensure NO verification email was sent during registration
    verification_emails = [
        m
        for m in email_service.outbox
        if m["recipient"] == test_email and m["email_type"] == "EMAIL_VERIFICATION"
    ]
    assert len(verification_emails) == 0

    # Immediate access to protected endpoints using the registration session token
    reg_token = reg_json["access_token"]
    me_immediate = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    assert me_immediate.status_code == 200
    assert me_immediate.json()["email"] == test_email

    drones_immediate = client.get(
        "/api/v1/drones",
        headers={"Authorization": f"Bearer {reg_token}", "User-Agent": "Mozilla/5.0"},
    )
    assert drones_immediate.status_code == 200

    # 5. Reject duplicate email registration
    dup_res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Duplicate User",
            "email": test_email,
            "password": short_initial_password,
            "confirm_password": short_initial_password,
        },
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()

    # 6. Even if a legacy database record had is_email_verified=False / PENDING_VERIFICATION,
    # login must NOT be blocked
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == test_email).first()
        u.is_email_verified = False
        u.account_status = "PENDING_VERIFICATION"
        db.commit()
    finally:
        db.close()

    login_res = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": short_initial_password, "remember_me": True},
    )
    assert login_res.status_code == 200, login_res.text
    login_json = login_res.json()
    assert login_json["user"]["account_status"] == "ACTIVE"
    assert login_json["user"]["is_email_verified"] is True
    pre_reset_token = login_json["access_token"]

    # 7. Invalid credentials return a clear error
    bad_login = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": "wrong"},
    )
    assert bad_login.status_code == 400
    assert "Incorrect email or password" in bad_login.json()["detail"]

    # 8. Forgot Password sends real password reset email
    forgot_res = client.post(
        "/api/auth/forgot-password",
        json={"email": test_email},
    )
    assert forgot_res.status_code == 200
    assert "If an account exists for this email address" in forgot_res.json()["message"]

    reset_emails = [
        m
        for m in email_service.outbox
        if m["recipient"] == test_email and m["email_type"] == "PASSWORD_RESET"
    ]
    assert len(reset_emails) == 1
    reset_url = reset_emails[-1]["action_url"]
    raw_reset_token = reset_url.split("token=")[1]

    # Verify reset token endpoint
    verify_res = client.get(f"/api/auth/verify-reset-token?token={raw_reset_token}")
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True

    # 9. Reset password accepts a short non-empty password ("sky7") without 12-char requirement
    success_reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw_reset_token,
            "new_password": short_new_password,
            "confirm_password": short_new_password,
        },
    )
    assert success_reset.status_code == 200, success_reset.text
    assert success_reset.json()["success"] is True

    # Pre-reset session is invalidated
    client.cookies.clear()
    invalidated_me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {pre_reset_token}"},
    )
    assert invalidated_me.status_code == 401

    # 10. Reuse of used reset token or expired token is rejected
    reuse_reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw_reset_token,
            "new_password": "another",
            "confirm_password": "another",
        },
    )
    assert reuse_reset.status_code == 400

    expired_raw_token = secrets.token_urlsafe(32)
    expired_hash = hashlib.sha256(expired_raw_token.encode("utf-8")).hexdigest()
    db = SessionLocal()
    try:
        db.add(
            PasswordReset(
                user_id=user_data["id"],
                token_hash=expired_hash,
                expires_at=get_utc_now() - timedelta(minutes=5),
            )
        )
        db.commit()
    finally:
        db.close()

    expired_reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": expired_raw_token,
            "new_password": "another",
            "confirm_password": "another",
        },
    )
    assert expired_reset.status_code == 400

    # 11. Login with updated short password succeeds and logout invalidates session
    new_login = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": short_new_password, "remember_me": False},
    )
    assert new_login.status_code == 200
    new_session_token = new_login.json()["access_token"]

    logout_res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {new_session_token}"},
    )
    assert logout_res.status_code == 200
    client.cookies.clear()

    revoked_me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_session_token}"},
    )
    assert revoked_me.status_code == 401


def test_forgot_password_rate_limiting():
    """Verify repeated password recovery requests are rate-limited."""
    reset_rate_limits()
    target_email = "ratelimit.test@garuda.aero"

    for _ in range(5):
        res = client.post("/api/auth/forgot-password", json={"email": target_email})
        assert res.status_code == 200

    sixth_res = client.post("/api/auth/forgot-password", json={"email": target_email})
    assert sixth_res.status_code == 429
    reset_rate_limits()
