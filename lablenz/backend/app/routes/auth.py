"""
Authentication routes.

Login flow:
  1. POST /auth/login
     - Verifies credentials.
     - Queries active UserFacility assignments.
     - 0 assignments  → 403
     - 1 assignment   → issues access + refresh tokens immediately.
     - 2+ assignments → issues a 5-min facility_selection token and returns
                        the assignment list so the client can render a picker.

  2. POST /auth/facility-select  (multi-facility only)
     - Accepts the selection_token + chosen facility_id.
     - Validates the choice against the user's active assignments.
     - Issues full access + refresh tokens.

Token transport: tokens are returned in the JSON body AND set as httpOnly
cookies (Secure in production) so both SPA and server-side rendering work.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from ..config import settings
from ..db.session import get_session
from ..dependencies.auth import COOKIE_NAME, get_token_data
from ..models.enums import OrgRole
from ..models.facility import Facility, UserFacility
from ..models.user import (
    FacilityOption,
    FacilitySelect,
    FacilitySelectionRequired,
    RefreshToken,
    Token,
    TokenData,
    User,
    UserLogin,
)
from ..security.jwt import (
    create_access_token,
    create_facility_selection_token,
    create_refresh_token,
    decode_facility_selection_token,
    decode_refresh_token,
)
from ..security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token_pair(user: User, facility: UserFacility, response: Response) -> Token:
    """
    Issue an access + refresh token for the given user/facility context,
    set httpOnly cookies, and return the Token schema.
    """
    token_payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
        "org_role": facility.org_role.value,
        "facility_id": facility.facility_id,
    }

    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token({"sub": str(user.id), "user_id": user.id})

    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # httpOnly cookie — prevents JS access (XSS mitigation)
    # SameSite=lax blocks CSRF on cross-site navigations while allowing normal links
    _set_auth_cookies(response, access_token, refresh_token)

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/auth/refresh",  # Scope cookie to refresh endpoint only
    )


def _get_active_assignments(
    user_id: int, session: Session
) -> list[tuple[UserFacility, Facility]]:
    """Return active (UserFacility, Facility) pairs for a user."""
    rows = session.exec(
        select(UserFacility, Facility)
        .join(Facility, UserFacility.facility_id == Facility.id)  # type: ignore[arg-type]
        .where(
            UserFacility.user_id == user_id,
            UserFacility.is_active == True,  # noqa: E712
        )
    ).all()
    return list(rows)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/login", response_model=Token | FacilitySelectionRequired)
def login(
    body: UserLogin,
    response: Response,
    session: Session = Depends(get_session),
) -> Token | FacilitySelectionRequired:
    """
    Authenticate with username + password.

    Single-facility users receive tokens immediately.
    Multi-facility users receive a facility selection token and the list of
    their active assignments to render a context picker.
    """
    # 1. Look up user
    user = session.exec(select(User).where(User.username == body.username.lower())).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Check facility assignments
    assignments = _get_active_assignments(user.id, session)  # type: ignore[arg-type]
    if not assignments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active facility assignments. Contact your administrator.",
        )

    # 3a. Single assignment — issue tokens directly
    if len(assignments) == 1:
        uf, _facility = assignments[0]
        return _build_token_pair(user, uf, response)

    # 3b. Multiple assignments — return selection data
    facilities = [
        FacilityOption(
            facility_id=facility.id,  # type: ignore[arg-type]
            facility_name=facility.name,
            org_role=uf.org_role,
        )
        for uf, facility in assignments
    ]
    selection_token = create_facility_selection_token(user.id)  # type: ignore[arg-type]

    return FacilitySelectionRequired(
        selection_required=True,
        facilities=facilities,
        selection_token=selection_token,
    )


@router.post("/facility-select", response_model=Token)
def facility_select(
    body: FacilitySelect,
    response: Response,
    session: Session = Depends(get_session),
) -> Token:
    """
    Complete login for a multi-facility user by selecting a facility context.
    Requires the selection_token returned by POST /auth/login.
    """
    # 1. Validate selection token
    user_id = decode_facility_selection_token(body.selection_token)

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 2. Verify the chosen facility is among the user's active assignments
    uf = session.exec(
        select(UserFacility).where(
            UserFacility.user_id == user_id,
            UserFacility.facility_id == body.facility_id,
            UserFacility.is_active == True,  # noqa: E712
        )
    ).first()

    if not uf:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active assignment for the selected facility",
        )

    return _build_token_pair(user, uf, response)


@router.post("/refresh", response_model=Token)
def refresh_token(
    body: RefreshToken,
    response: Response,
    session: Session = Depends(get_session),
) -> Token:
    """
    Exchange a valid refresh token for a new access token.
    Refreshes both access and refresh tokens (token rotation).
    """
    payload = decode_refresh_token(body.refresh_token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Re-fetch the active assignment that was encoded in the original access token.
    # The refresh token does not carry facility context — we look up the single
    # active assignment, or return 401 if the user has been deactivated / reassigned.
    assignments = _get_active_assignments(user.id, session)  # type: ignore[arg-type]
    if len(assignments) == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active facility assignments",
        )
    if len(assignments) > 1:
        # Client must re-login to pick a new context
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple facility contexts — please log in again to select a context",
        )

    uf, _facility = assignments[0]
    return _build_token_pair(user, uf, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear auth cookies. Clients should also discard stored tokens."""
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax", path="/auth/refresh")
