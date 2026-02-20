"""add risk_items table

Revision ID: 7f1a2c3d4e5f
Revises: 6c1d2f8a9b12
Create Date: 2026-01-24 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f1a2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '6c1d2f8a9b12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'risk_items' in inspector.get_table_names():
        return

    op.create_table(
        'risk_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('apr_id', sa.Integer(), nullable=False),
        sa.Column('step_id', sa.Integer(), nullable=False),
        sa.Column('hazard_id', sa.Integer(), nullable=True),
        sa.Column('risk_description', sa.Text(), nullable=False),
        sa.Column('probability', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('severity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('risk_level', sa.String(length=20), nullable=False, server_default='invalid'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['apr_id'], ['aprs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['passos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hazard_id'], ['perigos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_risk_items_apr_id'), 'risk_items', ['apr_id'], unique=False)
    op.create_index(op.f('ix_risk_items_step_id'), 'risk_items', ['step_id'], unique=False)
    op.create_index(op.f('ix_risk_items_hazard_id'), 'risk_items', ['hazard_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'risk_items' not in inspector.get_table_names():
        return

    op.drop_index(op.f('ix_risk_items_hazard_id'), table_name='risk_items')
    op.drop_index(op.f('ix_risk_items_step_id'), table_name='risk_items')
    op.drop_index(op.f('ix_risk_items_apr_id'), table_name='risk_items')
    op.drop_table('risk_items')
