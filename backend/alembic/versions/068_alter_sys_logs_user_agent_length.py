"""068_alter_sys_logs_user_agent_length

Revision ID: a1b2c3d4e5f6
Revises: e51127e9aa4a
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e51127e9aa4a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('sys_logs', 'user_agent',
                    existing_type=sa.VARCHAR(length=255),
                    type_=sa.VARCHAR(length=500),
                    existing_nullable=True)


def downgrade():
    op.alter_column('sys_logs', 'user_agent',
                    existing_type=sa.VARCHAR(length=500),
                    type_=sa.VARCHAR(length=255),
                    existing_nullable=True)
