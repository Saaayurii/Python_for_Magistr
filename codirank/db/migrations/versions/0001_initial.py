"""Initial schema with all tables and pgvector HNSW index

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('settings', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('status', sa.String(20), server_default='active', nullable=True),
        sa.Column('profile_vec', sa.Text(), nullable=True),  # will be cast by pgvector
        sa.Column('attributes', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('turn_count', sa.Integer(), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'apps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(10), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('developer', sa.Text(), nullable=True),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('rating', sa.Numeric(3, 2), nullable=True),
        sa.Column('rating_count', sa.Integer(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), server_default='0', nullable=True),
        sa.Column('has_ads', sa.Boolean(), nullable=True),
        sa.Column('has_iap', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_desc', sa.Text(), nullable=True),
        sa.Column('languages', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('permissions', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('icon_url', sa.Text(), nullable=True),
        sa.Column('store_url', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('embedding', sa.Text(), nullable=True),  # vector type handled by pgvector
        sa.Column('indexed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )

    op.create_table(
        'turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('app_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('signal', sa.String(20), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes
    op.create_index('ix_sessions_user_status', 'sessions', ['user_id', 'status'])
    op.create_index('ix_turns_session_index', 'turns', ['session_id', 'turn_index'])
    op.create_index('ix_feedback_session_app', 'feedback', ['session_id', 'app_id'])

    # HNSW index for vector similarity - requires pgvector to be installed
    op.execute("""
        ALTER TABLE apps ALTER COLUMN embedding TYPE vector(3584)
        USING embedding::vector(3584)
    """)
    op.execute("""
        ALTER TABLE sessions ALTER COLUMN profile_vec TYPE vector(3584)
        USING profile_vec::vector(3584)
    """)
    op.execute("""
        ALTER TABLE turns ALTER COLUMN embedding TYPE vector(3584)
        USING embedding::vector(3584)
    """)
    op.execute("""
        CREATE INDEX ON apps USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_table('turns')
    op.drop_table('apps')
    op.drop_table('sessions')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS vector")
