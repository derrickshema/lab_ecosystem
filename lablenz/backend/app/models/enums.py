import enum

class SystemRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    USER = "user"

class OrgRole(str, enum.Enum):
    IT_PERSONNEL = "it_personnel"
    PROVIDER = "provider"
    LAB_TECHNICIAN = "lab_technician"
    REGISTRATION_PERSONNEL = "registration_personnel"
    PATIENT = "patient"