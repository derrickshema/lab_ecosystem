import re
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import Field

from .enums import OrgRole, SystemRole


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


class RefreshToken(BaseModel):
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")


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


class UserEmailVerification(BaseModel):
    email: EmailStr = Field(max_length=100, description="Email address of the user requesting email verification")


class UserEmailVerificationConfirm(BaseModel):
    token: str = Field(description="Email verification token sent to the user's email")


# --- Multi-facility login schemas ---

class FacilityOption(BaseModel):
    """A facility + role assignment returned when a user has multiple active contexts."""
    facility_id: int
    facility_name: str
    org_role: OrgRole


class FacilitySelectionRequired(BaseModel):
    """Login response when the user has more than one active UserFacility assignment."""
    selection_required: Literal[True] = True
    facilities: list[FacilityOption]
    selection_token: str = Field(description="Short-lived token used to complete facility selection")


class FacilitySelect(BaseModel):
    """Request body for POST /auth/facility-select."""
    facility_id: int
    selection_token: str
