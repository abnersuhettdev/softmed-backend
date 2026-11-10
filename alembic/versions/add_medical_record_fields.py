"""add_medical_record_fields

Revision ID: add_medical_record_fields
Revises: 4c3f2d7fafb1
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_medical_record_fields'
down_revision = '4c3f2d7fafb1'  # Latest migration: add_google_oauth_fields_to_user
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to medical_records table
    op.add_column('medical_records', sa.Column('doctor_id', sa.Integer(), nullable=True))
    op.add_column('medical_records', sa.Column('session_id', sa.Integer(), nullable=True))
    op.add_column('medical_records', sa.Column('complaints', sa.Text(), nullable=True))
    op.add_column('medical_records', sa.Column('symptoms', sa.Text(), nullable=True))
    op.add_column('medical_records', sa.Column('conduct', sa.Text(), nullable=True))
    op.add_column('medical_records', sa.Column('orientation', sa.Text(), nullable=True))
    
    # Add foreign key constraint for doctor_id
    op.create_foreign_key(
        'fk_medical_records_doctor_id',
        'medical_records',
        'users',
        ['doctor_id'],
        ['id']
    )
    
    # Note: diagnosis and treatment are already nullable in the initial migration


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('fk_medical_records_doctor_id', 'medical_records', type_='foreignkey')
    
    # Remove new columns
    op.drop_column('medical_records', 'orientation')
    op.drop_column('medical_records', 'conduct')
    op.drop_column('medical_records', 'symptoms')
    op.drop_column('medical_records', 'complaints')
    op.drop_column('medical_records', 'session_id')
    op.drop_column('medical_records', 'doctor_id')
    
    # Note: diagnosis and treatment remain nullable

