"""
Facility and staff-access routes. SUPER_ADMIN only for now; facility IT
personnel managing their own staff can be added later.

Endpoints:
  POST   /facilities                                — create a facility
  GET    /facilities                                — list facilities
  GET    /facilities/{facility_id}/staff            — list staff assignments
  POST   /facilities/{facility_id}/staff            — grant a user a role here
  DELETE /facilities/{facility_id}/staff/{id}       — revoke (deactivate) a grant
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..db import get_session
from ..dependencies.rbac import get_superadmin
from ..models.facility import (
    Facility,
    FacilityCreate,
    FacilityRead,
    StaffAssignmentCreate,
    StaffAssignmentRead,
    UserFacility,
)
from ..models.user import User

router = APIRouter(prefix="/facilities", tags=["facilities"], dependencies=[Depends(get_superadmin)])


def _get_facility(facility_id: uuid.UUID, session: Session) -> Facility:
    facility = session.get(Facility, facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return facility


@router.post("", response_model=FacilityRead, status_code=status.HTTP_201_CREATED)
def create_facility(body: FacilityCreate, session: Session = Depends(get_session)) -> Facility:
    if body.code and session.exec(select(Facility).where(Facility.code == body.code)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Facility code already in use")
    facility = Facility(**body.model_dump())
    session.add(facility)
    session.commit()
    session.refresh(facility)
    return facility


@router.get("", response_model=list[FacilityRead])
def list_facilities(session: Session = Depends(get_session)) -> list[Facility]:
    return list(session.exec(select(Facility).order_by(Facility.name)).all())


@router.get("/{facility_id}/staff", response_model=list[StaffAssignmentRead])
def list_staff(facility_id: uuid.UUID, session: Session = Depends(get_session)) -> list[UserFacility]:
    _get_facility(facility_id, session)
    return list(session.exec(select(UserFacility).where(UserFacility.facility_id == facility_id)).all())


@router.post("/{facility_id}/staff", response_model=StaffAssignmentRead, status_code=status.HTTP_201_CREATED)
def grant_access(
    facility_id: uuid.UUID,
    body: StaffAssignmentCreate,
    session: Session = Depends(get_session),
) -> UserFacility:
    """Grant a user a role at this facility. Re-activates a previously revoked grant."""
    _get_facility(facility_id, session)
    if not session.get(User, body.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = session.exec(
        select(UserFacility).where(
            UserFacility.user_id == body.user_id,
            UserFacility.facility_id == facility_id,
            UserFacility.org_role == body.org_role,
        )
    ).first()
    if existing and existing.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has this role here")

    if existing:
        existing.is_active = True
        existing.deactivated_at = None
        existing.assigned_at = datetime.now(timezone.utc)
        assignment = existing
    else:
        assignment = UserFacility(user_id=body.user_id, facility_id=facility_id, org_role=body.org_role)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment


@router.delete("/{facility_id}/staff/{assignment_id}", response_model=StaffAssignmentRead)
def revoke_access(
    facility_id: uuid.UUID,
    assignment_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> UserFacility:
    """Deactivate a grant. The record is kept for the audit trail, never deleted."""
    assignment = session.get(UserFacility, assignment_id)
    if not assignment or assignment.facility_id != facility_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.is_active:
        assignment.is_active = False
        assignment.deactivated_at = datetime.now(timezone.utc)
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
    return assignment
