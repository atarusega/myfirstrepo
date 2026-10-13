"""band price reminder timestamp

Revision ID: c82c2579d179
Revises: db4d70d6040a
Create Date: 2026-09-26 09:54:03.441014
"""
import sqlalchemy as sa
from alembic import op

revision = 'c82c2579d179'
down_revision = 'db4d70d6040a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_reminder_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.drop_column('price_reminder_at')
