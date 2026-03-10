"""066_add_custom_prompt_is_full_template

Revision ID: a1b2c3d4e5f6
Revises: 8ff90df7871d
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '8ff90df7871d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('custom_prompt', sa.Column('is_full_template', sa.Boolean(), nullable=True))
    op.execute("UPDATE custom_prompt SET is_full_template = false WHERE is_full_template IS NULL")


def downgrade():
    op.drop_column('custom_prompt', 'is_full_template')
