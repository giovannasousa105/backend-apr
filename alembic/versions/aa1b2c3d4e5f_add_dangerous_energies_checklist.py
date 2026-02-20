"""add dangerous energies checklist to aprs

Revision ID: aa1b2c3d4e5f
Revises: 9a3d4e5f6b7c
Create Date: 2026-01-24 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '9a3d4e5f6b7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('aprs')}

    with op.batch_alter_table('aprs') as batch_op:
        if 'dangerous_energies_checklist' not in columns:
            batch_op.add_column(sa.Column('dangerous_energies_checklist', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('aprs')}

    with op.batch_alter_table('aprs') as batch_op:
        if 'dangerous_energies_checklist' in columns:
            batch_op.drop_column('dangerous_energies_checklist')
