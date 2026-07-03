"""expand users with audit roles and self refs

Revision ID: f22d8a4f14d1
Revises: cfa38db44517
Create Date: 2026-06-23 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f22d8a4f14d1'
down_revision: Union[str, Sequence[str], None] = 'cfa38db44517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


role_enum = sa.Enum('user', 'admin', 'superadmin', name='user_role', native_enum=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('roles', postgresql.ARRAY(role_enum), nullable=False, server_default=sa.text("ARRAY['user']::varchar[]")))
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))
    op.add_column('users', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))
    op.add_column('users', sa.Column('updated_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f('fk_users_created_by_id_users'),
        'users',
        'users',
        ['created_by_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_users_updated_by_id_users'),
        'users',
        'users',
        ['updated_by_id'],
        ['id'],
        ondelete='SET NULL',
    )

    op.alter_column('users', 'is_active', server_default=None)
    op.alter_column('users', 'is_deleted', server_default=None)
    op.alter_column('users', 'roles', server_default=None)
    op.alter_column('users', 'created_at', server_default=None)
    op.alter_column('users', 'updated_at', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('fk_users_updated_by_id_users'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('fk_users_created_by_id_users'), 'users', type_='foreignkey')
    op.drop_column('users', 'updated_by_id')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_by_id')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'roles')
    op.drop_column('users', 'is_deleted')
    op.drop_column('users', 'is_active')