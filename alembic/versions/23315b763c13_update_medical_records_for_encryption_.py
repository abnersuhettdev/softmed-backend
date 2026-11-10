"""update_medical_records_for_encryption_and_signature

Revision ID: 23315b763c13
Revises: add_medical_record_fields
Create Date: 2025-12-15 08:43:22.861863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23315b763c13'
down_revision: Union[str, None] = 'add_medical_record_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add consultation_id column
    op.add_column('medical_records', sa.Column('consultation_id', sa.Integer(), nullable=True))
    
    # Add encryption columns
    op.add_column('medical_records', sa.Column('encrypted_data', sa.Text(), nullable=True))
    op.add_column('medical_records', sa.Column('encryption_iv', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('encryption_auth_tag', sa.String(), nullable=True))
    
    # Add signature columns
    op.add_column('medical_records', sa.Column('is_signed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('medical_records', sa.Column('signed_at', sa.DateTime(), nullable=True))
    op.add_column('medical_records', sa.Column('signature_token', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('signature_hash', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('vidaas_document_id', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('signature_metadata', sa.JSON(), nullable=True))
    
    # Add prescription columns
    op.add_column('medical_records', sa.Column('prescription_id', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('prescription_token', sa.String(), nullable=True))
    op.add_column('medical_records', sa.Column('prescription_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove prescription columns
    op.drop_column('medical_records', 'prescription_metadata')
    op.drop_column('medical_records', 'prescription_token')
    op.drop_column('medical_records', 'prescription_id')
    
    # Remove signature columns
    op.drop_column('medical_records', 'signature_metadata')
    op.drop_column('medical_records', 'vidaas_document_id')
    op.drop_column('medical_records', 'signature_hash')
    op.drop_column('medical_records', 'signature_token')
    op.drop_column('medical_records', 'signed_at')
    op.drop_column('medical_records', 'is_signed')
    
    # Remove encryption columns
    op.drop_column('medical_records', 'encryption_auth_tag')
    op.drop_column('medical_records', 'encryption_iv')
    op.drop_column('medical_records', 'encrypted_data')
    
    # Remove consultation_id
    op.drop_column('medical_records', 'consultation_id')
