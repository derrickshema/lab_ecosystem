"""
RBAC Module

This module handles role-based access control -- determining WHAT the user can do.
Use these dependencies as route guards after get_current_user has established identity.
"""

from fastapi import Depends, HTTPException, status

from ..models.enums import OrgRole, SystemRole
from ..models.auth import TokenData
from ..models.user import User
from .auth import get_current_user, get_token_data, get_verified_user


def require_system_role(*roles: SystemRole):
    """
    Dependency factory: require the user to hold one of the given system roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_system_role(SystemRole.SUPER_ADMIN))])
        # or as a typed dependency that also returns the user:
        @router.get("/admin")
        async def admin_route(user: User = Depends(require_system_role(SystemRole.SUPER_ADMIN))):
            ...
    """
    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _guard


def require_org_role(*roles: OrgRole):
    """
    Dependency factory: require the user's session context to carry one of the
    given organisation roles (read from JWT claims, set at login from UserFacility).

    JWT-based check: stateless, no extra DB query.
    For high-sensitivity endpoints, additionally verify UserFacility.is_active
    directly in the route handler.

    Usage:
        @router.post("/sample", dependencies=[Depends(require_org_role(OrgRole.LAB_TECHNICIAN))])
    """
    async def _guard(
        current_user: User = Depends(get_current_user),
        token_data: TokenData = Depends(get_token_data),
    ) -> User:
        # get_token_data is cached by FastAPI — JWT decoded once even with both guards active
        if token_data.org_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _guard


# --- Convenience dependencies ---

async def get_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Require SUPER_ADMIN system role. Use as a direct Depends() in route signatures."""
    if current_user.role != SystemRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def get_verified_superadmin(current_user: User = Depends(get_verified_user)) -> User:
    """Require verified email AND SUPER_ADMIN role."""
    if current_user.role != SystemRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
