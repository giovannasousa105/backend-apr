"""add default probability/severity to perigos

Revision ID: 9a3d4e5f6b7c
Revises: 7f1a2c3d4e5f
Create Date: 2026-01-24 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3d4e5f6b7c'
down_revision: Union[str, Sequence[str], None] = '7f1a2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('perigos')}

    with op.batch_alter_table('perigos') as batch_op:
        if 'default_severity' not in columns:
            batch_op.add_column(
                sa.Column('default_severity', sa.Integer(), nullable=False, server_default='0')
            )
        if 'default_probability' not in columns:
            batch_op.add_column(
                sa.Column('default_probability', sa.Integer(), nullable=False, server_default='0')
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('perigos')}

    with op.batch_alter_table('perigos') as batch_op:
        if 'default_probability' in columns:
            batch_op.drop_column('default_probability')
        if 'default_severity' in columns:
            batch_op.drop_column('default_severity')
