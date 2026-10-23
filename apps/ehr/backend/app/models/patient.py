import uuid
from datetime import date, datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, UniqueConstraint, func
from sqlmodel import Column, Field, SQLModel

from .enums import Sex


class Patient(SQLModel, table=True):
    """
    A patient's record at one facility (identified there by MRN).

    The same person visiting two facilities has two Patient records, linked by
    platform_patient_id — the facility-independent identity owned by the
    Identity/Platform service (see docs/architecture/DATA_OWNERSHIP.md).

    IDs owned by other services (facility, platform patient, staff) are plain
    UUID columns, never foreign keys: those tables live in other databases.
    """
    __table_args__ = (
        UniqueConstraint("facility_id", "mrn", name="uq_patient_facility_mrn"),
        UniqueConstraint("facility_id", "platform_patient_id", name="uq_patient_facility_platform_patient"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    facility_id: uuid.UUID = Field(index=True, description="Facility this record belongs to (Identity/Platform)")
    mrn: str = Field(max_length=50, description="Medical record number, unique within the facility")
    platform_patient_id: uuid.UUID | None = Field(
        default=None,
        index=True,
        description="Cross-facility identity (Identity/Platform). Null until linked.",
    )

    first_name: str = Field(max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    last_name: str = Field(max_length=50, index=True)
    date_of_birth: date
    sex: Sex = Field(sa_column=Column(SAEnum(Sex, name="sex", create_type=True), nullable=False))
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)

    registered_by_id: uuid.UUID = Field(description="Registration personnel who created the record (staff user ID)")
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
