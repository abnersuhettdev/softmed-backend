"""add_announcements_table

Revision ID: 2a3b4c5d6e7f
Revises: 178f43370cc0
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '178f43370cc0'  # add_photo_to_user
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create announcement type enum using raw SQL to avoid duplicate creation
    conn = op.get_bind()
    
    # Use DO block to create enum only if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE announcementtype AS ENUM ('info', 'success', 'warning', 'error');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Check if tables already exist (in case of partial migration)
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create announcements table using raw SQL to avoid enum creation issues
    if 'announcements' not in existing_tables:
        op.execute("""
            CREATE TABLE announcements (
                id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL,
                message TEXT NOT NULL,
                type announcementtype NOT NULL,
                recipient_id INTEGER,
                created_by_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                CONSTRAINT fk_announcements_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
                CONSTRAINT fk_announcements_recipient FOREIGN KEY (recipient_id) REFERENCES users(id)
            )
        """)
        op.create_index('ix_announcements_id', 'announcements', ['id'], unique=False)
        op.create_index('ix_announcements_recipient_id', 'announcements', ['recipient_id'], unique=False)
    
    # Create announcement_reads table
    if 'announcement_reads' not in existing_tables:
        op.create_table(
        'announcement_reads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('announcement_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['announcement_id'], ['announcements.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_announcement_reads_id'), 'announcement_reads', ['id'], unique=False)
        op.create_index(op.f('ix_announcement_reads_announcement_id'), 'announcement_reads', ['announcement_id'], unique=False)
        op.create_index(op.f('ix_announcement_reads_user_id'), 'announcement_reads', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_announcement_reads_user_id'), table_name='announcement_reads')
    op.drop_index(op.f('ix_announcement_reads_announcement_id'), table_name='announcement_reads')
    op.drop_index(op.f('ix_announcement_reads_id'), table_name='announcement_reads')
    op.drop_table('announcement_reads')
    op.drop_index(op.f('ix_announcements_recipient_id'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_id'), table_name='announcements')
    op.drop_table('announcements')
    
    # Drop enum type
    announcement_type_enum = sa.Enum(name='announcementtype')
    announcement_type_enum.drop(op.get_bind())

