"""067_biz_dictionary

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'biz_dict',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('oid', sa.BigInteger(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('oid', 'code', name='uq_biz_dict_oid_code'),
    )
    op.create_index('ix_biz_dict_oid', 'biz_dict', ['oid'])

    op.create_table(
        'biz_dict_item',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('dict_id', sa.BigInteger(), nullable=False),
        sa.Column('item_code', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False),
        sa.Column('item_name', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False),
        sa.Column('sort', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['dict_id'], ['biz_dict.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dict_id', 'item_code', name='uq_biz_dict_item_dict_code'),
    )
    op.create_index('ix_biz_dict_item_dict_id', 'biz_dict_item', ['dict_id'])

    op.create_table(
        'biz_dict_binding',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('dict_id', sa.BigInteger(), nullable=False),
        sa.Column('datasource_id', sa.BigInteger(), nullable=False),
        sa.Column('table_name', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False),
        sa.Column('column_name', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['dict_id'], ['biz_dict.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'datasource_id', 'table_name', 'column_name',
            name='uq_biz_dict_binding_ds_table_col',
        ),
    )
    op.create_index('ix_biz_dict_binding_ds', 'biz_dict_binding', ['datasource_id'])


def downgrade():
    op.drop_index('ix_biz_dict_binding_ds', table_name='biz_dict_binding')
    op.drop_table('biz_dict_binding')
    op.drop_index('ix_biz_dict_item_dict_id', table_name='biz_dict_item')
    op.drop_table('biz_dict_item')
    op.drop_index('ix_biz_dict_oid', table_name='biz_dict')
    op.drop_table('biz_dict')
