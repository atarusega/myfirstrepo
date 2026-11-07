"""consent version, video reminder, fsm states

Revision ID: 5b1e7a3c9d20
Revises: c82c2579d179
Create Date: 2026-10-12 12:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = '5b1e7a3c9d20'
down_revision = 'c82c2579d179'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('consent_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('video_reminder_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        'fsm_states',
        sa.Column('key', sa.String(length=200), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('key', name=op.f('fsm_states_pkey')),
    )


def downgrade() -> None:
    op.drop_table('fsm_states')
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.drop_column('video_reminder_at')
        batch_op.drop_column('consent_version')
