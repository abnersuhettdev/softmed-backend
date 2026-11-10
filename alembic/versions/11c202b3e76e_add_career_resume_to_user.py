"""add_career_resume_to_user

Revision ID: 11c202b3e76e
Revises: add_doctor_specialty
Create Date: 2025-11-27 18:49:40.971534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11c202b3e76e'
down_revision: Union[str, None] = 'add_doctor_specialty'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('career_resume', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'career_resume')
