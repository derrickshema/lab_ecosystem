import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import DateTime, Enum as SAEnum, UniqueConstraint, func
from sqlmodel import Column, Field, SQLModel

from .enums import OrgRole


class Facility(SQLModel, table=True):
    """
    A healthcare facility (hospital, clinic, reference lab, etc.).

    The source of truth for facilities across the platform: other apps store
    facility_id as a plain UUID and read it from the access token.
    Each facility manages its own staff access via UserFacility records.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255, index=True, description="Full facility name")
    code: str | None = Field(
        default=None,
        max_length=50,
        unique=True,
        description="Short facility code for display/lookup, e.g. 'MCH-001'",
    )
    address: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
    )


class UserFacility(SQLModel, table=True):
    """
    Access grant: a user's role at a specific facility.

    This is the join table that answers: "what can this person do at this facility?"

    Key behaviours:
    - is_active=False when someone resigns — the User record is NEVER deleted
      (audit trail requires knowing who ordered/resulted a test, even post-resignation)
    - A user can hold different OrgRoles at different facilities (e.g. PROVIDER
      at Hospital A and LAB_TECHNICIAN at a reference lab)
    - The JWT carries (facility_id, org_role) for the selected session context;
      RBAC guards in every app validate against these JWT claims (stateless, fast)
    """
    __tablename__ = "user_facility"
    __table_args__ = (
        UniqueConstraint("user_id", "facility_id", "org_role", name="uq_user_facility_role"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    facility_id: uuid.UUID = Field(foreign_key="facility.id", index=True)
    org_role: OrgRole = Field(
        sa_column=Column(SAEnum(OrgRole, name="org_role", create_type=True), nullable=False),
        description="The user's role at this facility",
    )
    is_active: bool = Field(default=True, index=True, description="False when the user has left this facility")
    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="When IT provisioned this access",
    )
    deactivated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When access was revoked (resignation, role change, etc.)",
    )


# --- API schemas ---

class FacilityCreate(BaseModel):
    name: str = Field(max_length=255)
    code: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)


class FacilityRead(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None
    address: str | None
    created_at: datetime


class StaffAssignmentCreate(BaseModel):
    user_id: uuid.UUID
    org_role: OrgRole


class StaffAssignmentRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    facility_id: uuid.UUID
    org_role: OrgRole
    is_active: bool
    assigned_at: datetime
    deactivated_at: datetime | None
