import enum


class Sex(str, enum.Enum):
    """Administrative sex as recorded at registration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class EncounterStatus(str, enum.Enum):
    """
    Lifecycle of a visit:
    CHECKED_IN → ASSIGNED → IN_PROGRESS → COMPLETED
    Any state before COMPLETED can move to CANCELLED.
    """
    CHECKED_IN = "checked_in"      # registration opened the visit; awaiting a physician
    ASSIGNED = "assigned"          # clinical manager assigned a physician
    IN_PROGRESS = "in_progress"    # physician is seeing the patient
    COMPLETED = "completed"
    CANCELLED = "cancelled"
