import enum


class SystemRole(str, enum.Enum):
    """Platform-wide role, independent of any facility."""
    SUPER_ADMIN = "super_admin"
    USER = "user"


class OrgRole(str, enum.Enum):
    """
    Staff roles within a facility, shared by every app (EHR, LabLenz, ...).
    A user can hold different roles at different facilities.
    Patients are NOT staff and never hold an OrgRole.
    """
    IT_PERSONNEL = "it_personnel"
    REGISTRATION_PERSONNEL = "registration_personnel"  # EHR: registers patients, checks them in
    CLINICAL_MANAGER = "clinical_manager"              # EHR: assigns visits to physicians
    PROVIDER = "provider"                              # EHR: physician; sees patients, orders tests
    LAB_TECHNICIAN = "lab_technician"                  # LabLenz: specimens and results
