"""
User management routes.

All endpoints require authentication. Role-escalation is blocked at the
model layer (UserCreate.role is locked to USER).

Endpoints:
  GET    /users/me                 — current user profile
  PATCH  /users/me                 — update own profile (name/username/email)
  POST   /users/me/change-password — change own password
  POST   /users/                   — create a new user (SUPER_ADMIN only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..db.session import get_session
from ..dependencies.auth import get_current_user, get_verified_user
from ..dependencies.rbac import get_superadmin
from ..models.facility import UserFacility
from ..models.user import (
    User,
    UserCreate,
    UserPasswordChange,
    UserRead,
    UserUpdate,
)
from ..security.passwords import hash_password, verify_password, needs_rehash

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_verified_user),
    session: Session = Depends(get_session),
) -> User:
    """
    Update own profile fields (name, username, email).
    Requires email verification to change contact details.
    """
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )

    # Check username uniqueness if being changed
    if "username" in update_data and update_data["username"] != current_user.username:
        existing = session.exec(
            select(User).where(User.username == update_data["username"])
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    # Check email uniqueness if being changed
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = session.exec(
            select(User).where(User.email == update_data["email"])
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        # Email changed — require re-verification
        update_data["email_verified"] = False

    for field, value in update_data.items():
        setattr(current_user, field, value)

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """Change own password. Requires the current password for confirmation."""
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must differ from the current password",
        )
    current_user.hashed_password = hash_password(body.new_password)
    session.add(current_user)
    session.commit()


# ---------------------------------------------------------------------------
# Admin — user creation
# ---------------------------------------------------------------------------

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    _admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session),
) -> User:
    """
    Create a new clinical staff user. SUPER_ADMIN only.

    Optionally creates a UserFacility assignment if org_role + facility_id
    are supplied in the request body.
    """
    # Uniqueness checks
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    if session.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        first_name=body.first_name,
        middle_name=body.middle_name,
        last_name=body.last_name,
        username=body.username,
        email=body.email,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    session.add(user)
    session.flush()  # Assign user.id before creating UserFacility

    if body.org_role and body.facility_id:
        uf = UserFacility(
            user_id=user.id,
            facility_id=body.facility_id,
            org_role=body.org_role,
        )
        session.add(uf)

    session.commit()
    session.refresh(user)
    return user
