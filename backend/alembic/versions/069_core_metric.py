"""069 core_metric and metric_component

Revision ID: f1a2b3c4d5e6
Revises: e0e1f2a3b4c5
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

revision = 'f1a2b3c4d5e6'
down_revision = 'e0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'core_metric',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('oid', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('terminology_root_id', sa.BigInteger(), nullable=True),
        sa.Column('metric_kind', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('specific_ds', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('datasource_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('measure_sql', sa.Text(), nullable=True),
        sa.Column('base_metric_id', sa.BigInteger(), nullable=True),
        sa.Column('modifiers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('expansion_hint', sa.Text(), nullable=True),
        sa.Column('expression', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('oid', 'code', name='uq_core_metric_oid_code'),
    )
    op.create_index('ix_core_metric_oid', 'core_metric', ['oid'])
    op.create_index('ix_core_metric_enabled', 'core_metric', ['enabled'])
    op.create_index('ix_core_metric_kind', 'core_metric', ['metric_kind'])

    op.create_table(
        'metric_component',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('parent_metric_id', sa.BigInteger(), nullable=False),
        sa.Column('child_metric_id', sa.BigInteger(), nullable=False),
        sa.Column('slot_code', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_metric_id'], ['core_metric.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_metric_id'], ['core_metric.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('parent_metric_id', 'slot_code', name='uq_metric_component_parent_slot'),
    )
    op.create_index('ix_metric_component_parent', 'metric_component', ['parent_metric_id'])


def downgrade():
    op.drop_index('ix_metric_component_parent', table_name='metric_component')
    op.drop_table('metric_component')
    op.drop_index('ix_core_metric_kind', table_name='core_metric')
    op.drop_index('ix_core_metric_enabled', table_name='core_metric')
    op.drop_index('ix_core_metric_oid', table_name='core_metric')
    op.drop_table('core_metric')
