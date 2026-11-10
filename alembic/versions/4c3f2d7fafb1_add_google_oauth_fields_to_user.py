"""add_google_oauth_fields_to_user

Revision ID: 4c3f2d7fafb1
Revises: cdeda92a5021
Create Date: 2025-12-10 01:22:22.130492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c3f2d7fafb1'
down_revision: Union[str, None] = 'cdeda92a5021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google OAuth fields to users table
    op.add_column('users', sa.Column('google_access_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('google_refresh_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('google_calendar_enabled', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('profile_completed', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('google_token_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove Google OAuth fields from users table
    op.drop_column('users', 'google_token_expires_at')
    op.drop_column('users', 'profile_completed')
    op.drop_column('users', 'google_calendar_enabled')
    op.drop_column('users', 'google_refresh_token')
    op.drop_column('users', 'google_access_token')
