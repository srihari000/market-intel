"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('competitors', sa.JSON, nullable=True),
        sa.Column('topics', sa.JSON, nullable=True),
        sa.Column('source_urls', sa.JSON, nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_runs_user_id', 'runs', ['user_id'])

    op.create_table('reports',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('themes', sa.JSON, nullable=True),
        sa.Column('competitor_activities', sa.JSON, nullable=True),
        sa.Column('raw_sources', sa.JSON, nullable=True),
        sa.Column('hallucination_verdict', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )


def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('runs')
    op.drop_table('users')
