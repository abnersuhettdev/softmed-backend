"""Add doctor specialty field

Revision ID: add_doctor_specialty
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_doctor_specialty'
down_revision = 'fad5b50210e2'  # Latest migration: add_doctor_fields_to_user
branch_labels = None
depends_on = None


def upgrade():
    # Add specialty column to users table
    op.add_column('users', sa.Column('primary_specialty', sa.String(), nullable=True))
    # Create index for faster filtering
    op.create_index('ix_users_primary_specialty', 'users', ['primary_specialty'])


def downgrade():
    op.drop_index('ix_users_primary_specialty', table_name='users')
    op.drop_column('users', 'primary_specialty')

