"""add_vidaas_fields_to_user_and_medical_record

Revision ID: add_vidaas_fields
Revises: 23315b763c13
Create Date: 2025-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_vidaas_fields'
down_revision: Union[str, None] = '23315b763c13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Vidaas fields to users table (for doctors)
    op.add_column('users', sa.Column('vidaas_user_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('vidaas_certificate_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('vidaas_auth_token', sa.String(), nullable=True))
    
    # Add new Vidaas signature fields to medical_records table
    op.add_column('medical_records', sa.Column('signature_id', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('signed_hash', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('vidaas_certificate_id', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('vidaas_user_id', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove Vidaas fields from medical_records
    op.drop_column('medical_records', 'vidaas_user_id')
    op.drop_column('medical_records', 'vidaas_certificate_id')
    op.drop_column('medical_records', 'signed_hash')
    op.drop_column('medical_records', 'signature_id')
    
    # Remove Vidaas fields from users
    op.drop_column('users', 'vidaas_auth_token')
    op.drop_column('users', 'vidaas_certificate_id')
    op.drop_column('users', 'vidaas_user_id')

