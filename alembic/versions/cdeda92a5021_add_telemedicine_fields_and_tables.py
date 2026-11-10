"""add_telemedicine_fields_and_tables

Revision ID: cdeda92a5021
Revises: 2a3b4c5d6e7f
Create Date: 2025-12-05 23:24:05.247205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdeda92a5021'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('telemedicine_access', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('queue_open', sa.Boolean(), nullable=True))
    
    # Create settings table
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)
    
    # Create telemedicine_sessions table
    op.create_table(
        'telemedicine_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('meet_call_link', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telemedicine_sessions_status'), 'telemedicine_sessions', ['status'], unique=False)
    
    # Insert default telemedicine_enabled setting
    # Use a try-except approach since ON CONFLICT might not work in all PostgreSQL versions
    op.execute("""
        INSERT INTO settings (key, value, updated_at)
        SELECT 'telemedicine_enabled', 'true', NOW()
        WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key = 'telemedicine_enabled')
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_telemedicine_sessions_status'), table_name='telemedicine_sessions')
    op.drop_table('telemedicine_sessions')
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_table('settings')
    
    # Drop columns from users table
    op.drop_column('users', 'queue_open')
    op.drop_column('users', 'telemedicine_access')
