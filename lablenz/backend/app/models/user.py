from datetime import datetime, timezone
from enum import Enum
import re

from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import DateTime, func
from sqlmodel import Column, Field, SQLModel

from lablenz.backend.app.models.enums import OrgRole, SystemRole


class UserBase(SQLModel):
    first_name: str = Field(max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    last_name: str = Field(max_length=50)
    username: str = Field(index=True, unique=True, max_length=50, description="Unique username for the user")
    email: EmailStr = Field(index=True, unique=True, max_length=100, description="User's email address")
    role: SystemRole = Field(default=SystemRole.USER, sa_column = Column(Enum(SystemRole, name="system_role", create_type=True)), description="System role assigned to the user")

    @field_validator("username")
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.-]+$", value):
            raise ValueError("Username can only contain letters, numbers, underscores, hyphens, and periods.")
        return value.lower()  # Normalize to lowercase for consistency
    
    @field_validator("email")
    def validate_email(cls, value: str) -> str:
        return value.lower()
    
class User(UserBase, table=True):
    id: int|None = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255, description="Hashed password for the user")
    email_verified: bool = Field(default=False, description="Indicates whether the user's email has been verified")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()), description="Timestamp when the user was created")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc)), description="Timestamp when the user was last updated")

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=255, description="Password for the user (will be hashed before storage)")
    org_role: OrgRole|None = Field(default=None, description="Organization role assigned to the user (optional)")
    facility_id: int|None = Field(default=None, description="ID of the facility the user is associated with (optional)")

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character (@, $, !, %, *, ?, &).")
        return value

class UserRead(UserBase):
    id: int
    email_verified: bool
    created_at: datetime
    updated_at: datetime

class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    username: str | None = Field(default=None, max_length=50, description="Unique username for the user")
    email: EmailStr | None = Field(default=None, max_length=100, description="User's email address")
    role: SystemRole | None = Field(default=None, description="System role assigned to the user")
    org_role: OrgRole|None = Field(default=None, description="Organization role assigned to the user (optional)")
    facility_id: int|None = Field(default=None, description="ID of the facility the user is associated with (optional)")

    @field_validator("username")
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.-]+$", value):
            raise ValueError("Username can only contain letters, numbers, underscores, hyphens, and periods.")
        return value.lower()  # Normalize to lowercase for consistency
    
    @field_validator("email")
    def validate_email(cls, value: str) -> str:
        return value.lower()
    
class UserLogin(BaseModel):
    username: str = Field(max_length=50, description="Username for login")
    password: str = Field(max_length=255, description="Password for login")

class Token(BaseModel):
    access_token: str = Field(description="JWT access token for authentication")
    token_type: str = Field(default="bearer", description="Type of the token (default is 'bearer')")
    refresh_token: str | None = Field(default=None, description="JWT refresh token for obtaining new access tokens (optional)")
    expires_in: int = Field(description="Expiration time of the access token in seconds")

class TokenData(BaseModel):
    user_id: int = Field(description="User ID extracted from the token")
    username: str | None = Field(default=None, description="Username extracted from the token (optional)")
    role: SystemRole | None = Field(default=None, description="System role extracted from the token (optional)")
    org_role: OrgRole | None = Field(default=None, description="Organization role extracted from the token (optional)")
    facility_id: int | None = Field(default=None, description="Facility ID extracted from the token (optional)")

class UserPasswordChange(BaseModel):
    old_password: str = Field(max_length=255, description="Current password of the user")
    new_password: str = Field(min_length=8, max_length=255, description="New password for the user (will be hashed before storage)")

    @field_validator("new_password")
    def validate_new_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("New password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("New password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("New password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("New password must contain at least one special character (@, $, !, %, *, ?, &).")
        return value
    
class UserPasswordReset(BaseModel):
    email: EmailStr = Field(max_length=100, description="Email address of the user requesting password reset")

class UserPasswordResetConfirm(BaseModel):
    token: str = Field(description="Password reset token sent to the user's email")
    new_password: str = Field(min_length=8, max_length=255, description="New password for the user (will be hashed before storage)")

    @field_validator("new_password")
    def validate_new_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("New password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("New password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("New password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("New password must contain at least one special character (@, $, !, %, *, ?, &).")
        return value
    
class RefreshToken(BaseModel):
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")

class UserEmailVerification(BaseModel):
    email: EmailStr = Field(max_length=100, description="Email address of the user requesting email verification")

class UserEmailVerificationConfirm(BaseModel):
    token: str = Field(description="Email verification token sent to the user's email")