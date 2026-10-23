"""
Create the first SUPER_ADMIN from the SUPERADMIN_* settings.

    python -m scripts.create_superadmin

Safe to re-run: does nothing if that username already exists. The account is
created active (email treated as verified) so it can log in immediately.
"""

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models.enums import SystemRole
from app.models.user import User
from app.security.passwords import hash_password


def main() -> None:
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == settings.SUPERADMIN_USERNAME.lower())).first():
            print(f"Superadmin '{settings.SUPERADMIN_USERNAME}' already exists — nothing to do.")
            return
        session.add(User(
            first_name="Super",
            last_name="Admin",
            username=settings.SUPERADMIN_USERNAME.lower(),
            email=settings.SUPERADMIN_EMAIL.lower(),
            role=SystemRole.SUPER_ADMIN,
            hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
            account_active=True,
        ))
        session.commit()
        print(f"Created superadmin '{settings.SUPERADMIN_USERNAME}'.")


if __name__ == "__main__":
    main()
