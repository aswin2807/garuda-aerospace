import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from backend.app.core.config import settings


def _validate_non_empty_password(v: str) -> str:
    if not v or len(v) == 0:
        raise ValueError("Password is required")
    min_len = max(1, settings.MIN_PASSWORD_LENGTH)
    if len(v) < min_len:
        raise ValueError(f"Password must be at least {min_len} character(s) long")
    if len(v.encode("utf-8")) > settings.MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password cannot exceed {settings.MAX_PASSWORD_BYTES} bytes in UTF-8 encoding"
        )
    return v


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "OPERATOR"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v


class UserCreate(UserBase):
    password: str
    confirm_password: Optional[str] = None
    accept_terms: Optional[bool] = True

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_non_empty_password(v)

    @model_validator(mode="after")
    def validate_registration_fields(self) -> "UserCreate":
        resolved_name = (self.full_name or self.name or "").strip()
        if not resolved_name:
            raise ValueError("Full name is required")
        self.name = resolved_name
        self.full_name = resolved_name

        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self


class UserLogin(BaseModel):
    email: str
    password: str
    remember_me: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    full_name: Optional[str] = None
    role: str = "OPERATOR"
    is_active: bool
    is_email_verified: bool = True
    account_status: str = "ACTIVE"
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_full_name(self) -> "UserResponse":
        if not self.full_name:
            self.full_name = self.name
        return self


class RegisterResponse(BaseModel):
    success: bool = True
    message: str
    requires_verification: bool = False
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    success: bool
    message: str
    email: Optional[str] = None


class ResendVerificationRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v


class ResendVerificationResponse(BaseModel):
    success: bool
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v


class ForgotPasswordResponse(BaseModel):
    message: str


class VerifyResetTokenResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_non_empty_password(v)


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str


class LogoutResponse(BaseModel):
    success: bool
    message: str
