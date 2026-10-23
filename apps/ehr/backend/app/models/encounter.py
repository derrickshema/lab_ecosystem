import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, func
from sqlmodel import Column, Field, SQLModel

from .enums import EncounterStatus


class Encounter(SQLModel, table=True):
    """
    One visit by a patient to a facility.

    Flow:
    - Registration personnel check the patient in → CHECKED_IN
    - Clinical manager assigns a physician → ASSIGNED
      (every visit is assigned on its own; a return visit is a new Encounter)
    - Physician sees the patient → IN_PROGRESS → COMPLETED

    Staff are referenced by user ID from Identity/Platform (plain UUIDs, no FK).
    patient_id IS a foreign key: Patient lives in this same database.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    facility_id: uuid.UUID = Field(index=True, description="Copied from the patient for facility-scoped queries")
    patient_id: uuid.UUID = Field(foreign_key="patient.id", index=True)
    status: EncounterStatus = Field(
        default=EncounterStatus.CHECKED_IN,
        sa_column=Column(
            SAEnum(EncounterStatus, name="encounter_status", create_type=True),
            nullable=False,
            index=True,
        ),
    )
    reason_for_visit: str | None = Field(default=None, max_length=500)

    # Check-in (registration personnel)
    checked_in_by_id: uuid.UUID = Field(description="Registration personnel who opened the visit")
    checked_in_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    # Assignment (clinical manager → physician)
    assigned_physician_id: uuid.UUID | None = Field(default=None, index=True)
    assigned_by_id: uuid.UUID | None = Field(default=None, description="Clinical manager who made the assignment")
    assigned_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    ended_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the visit was completed or cancelled",
    )
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
