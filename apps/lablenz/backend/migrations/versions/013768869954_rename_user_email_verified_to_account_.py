"""rename user email_verified to account_active

Revision ID: 013768869954
Revises: 01c5465c1ff8
Create Date: 2026-10-23 12:11:49.563015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013768869954'
down_revision: Union[str, Sequence[str], None] = '01c5465c1ff8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Hand-written: autogenerate sees a rename as drop + add, which loses data.
    op.alter_column('user', 'email_verified', new_column_name='account_active')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user', 'account_active', new_column_name='email_verified')
