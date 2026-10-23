# Roles are shared by every app, so they live in labcore. Re-exported here so
# identity's models and routes keep importing from .enums.
from labcore.roles import OrgRole, SystemRole

__all__ = ["OrgRole", "SystemRole"]
