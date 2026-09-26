"""initial schema

Revision ID: db4d70d6040a
Revises: 
Create Date: 2026-09-26 09:50:59.934518
"""
import sqlalchemy as sa
from alembic import op

revision = 'db4d70d6040a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('bands',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('travel_scope', sa.String(length=20), nullable=True),
    sa.Column('lineup', sa.String(length=20), nullable=True),
    sa.Column('instruments', sa.JSON(), nullable=False),
    sa.Column('genres', sa.JSON(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price_private', sa.Integer(), nullable=True),
    sa.Column('price_corporate', sa.Integer(), nullable=True),
    sa.Column('price_newyear', sa.Integer(), nullable=True),
    sa.Column('program_format', sa.String(length=20), nullable=True),
    sa.Column('sound', sa.String(length=20), nullable=True),
    sa.Column('services', sa.JSON(), nullable=False),
    sa.Column('video_links', sa.JSON(), nullable=False),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('website', sa.String(length=300), nullable=True),
    sa.Column('tg_user_id', sa.BigInteger(), nullable=True),
    sa.Column('tg_username', sa.String(length=100), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('source_note', sa.Text(), nullable=True),
    sa.Column('claim_token', sa.String(length=40), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('reject_reason', sa.Text(), nullable=True),
    sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('prices_confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('bands_pkey')),
    sa.UniqueConstraint('claim_token', name=op.f('bands_claim_token_key'))
    )
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bands_tg_user_id'), ['tg_user_id'], unique=False)

    op.create_table('producers',
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=True),
    sa.Column('full_name', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('tg_user_id', name=op.f('producers_pkey'))
    )
    op.create_table('search_requests',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('producer_id', sa.BigInteger(), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('parsed', sa.JSON(), nullable=False),
    sa.Column('result_ids', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('search_requests_pkey'))
    )
    with op.batch_alter_table('search_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_search_requests_producer_id'), ['producer_id'], unique=False)

    op.create_table('leads',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('request_id', sa.Integer(), nullable=True),
    sa.Column('band_id', sa.Integer(), nullable=False),
    sa.Column('producer_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['band_id'], ['bands.id'], name=op.f('leads_band_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('leads_pkey'))
    )
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_leads_band_id'), ['band_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_leads_producer_id'), ['producer_id'], unique=False)

    op.create_table('recommendations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('band_id', sa.Integer(), nullable=False),
    sa.Column('recommender_tg_id', sa.BigInteger(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['band_id'], ['bands.id'], name=op.f('recommendations_band_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('recommendations_pkey')),
    sa.UniqueConstraint('band_id', 'recommender_tg_id', 'source', name=op.f('recommendations_band_id_recommender_tg_id_source_key'))
    )
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recommendations_band_id'), ['band_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recommendations_band_id'))

    op.drop_table('recommendations')
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_leads_producer_id'))
        batch_op.drop_index(batch_op.f('ix_leads_band_id'))

    op.drop_table('leads')
    with op.batch_alter_table('search_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_search_requests_producer_id'))

    op.drop_table('search_requests')
    op.drop_table('producers')
    with op.batch_alter_table('bands', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bands_tg_user_id'))

    op.drop_table('bands')
