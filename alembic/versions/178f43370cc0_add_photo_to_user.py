"""add_photo_to_user

Revision ID: 178f43370cc0
Revises: 11c202b3e76e
Create Date: 2025-11-27 19:19:07.509923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '178f43370cc0'
down_revision: Union[str, None] = '11c202b3e76e'  # add_career_resume_to_user
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('photo', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'photo')
