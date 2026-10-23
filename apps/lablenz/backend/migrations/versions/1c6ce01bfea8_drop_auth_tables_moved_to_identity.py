"""drop auth tables (moved to identity)

Users, facilities and role grants now live in apps/identity (identity_db).
LabLenz verifies Identity's tokens and stores user/facility IDs as plain UUIDs.

Hand-written: autogenerate dropped the tables in alphabetical order, which
fails because user_facility has foreign keys to facility and user. It also
left the enum types behind.

Revision ID: 1c6ce01bfea8
Revises: 013768869954
Create Date: 2026-10-23 14:06:34.208744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1c6ce01bfea8'
down_revision: Union[str, Sequence[str], None] = '013768869954'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Child table first: it references facility and user
    op.drop_table('user_facility')  # also drops its indexes
    op.drop_table('user')
    op.drop_table('facility')
    sa.Enum(name='org_role').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='system_role').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade schema: recreate the tables as they were at 013768869954 (empty)."""
    op.create_table('facility',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=True),
    sa.Column('address', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_facility_name'), 'facility', ['name'], unique=False)
    op.create_table('user',
    sa.Column('first_name', sa.String(length=50), nullable=False),
    sa.Column('middle_name', sa.String(length=50), nullable=True),
    sa.Column('last_name', sa.String(length=50), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('role', sa.Enum('SUPER_ADMIN', 'USER', name='system_role'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('account_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.create_table('user_facility',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('facility_id', sa.Integer(), nullable=False),
    sa.Column('org_role', sa.Enum('IT_PERSONNEL', 'PROVIDER', 'LAB_TECHNICIAN', 'REGISTRATION_PERSONNEL', name='org_role'), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'facility_id', 'org_role', name='uq_user_facility_role')
    )
    op.create_index(op.f('ix_user_facility_facility_id'), 'user_facility', ['facility_id'], unique=False)
    op.create_index(op.f('ix_user_facility_is_active'), 'user_facility', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_facility_user_id'), 'user_facility', ['user_id'], unique=False)
