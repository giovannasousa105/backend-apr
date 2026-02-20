"""add passo technical evidence fields

Revision ID: 6c1d2f8a9b12
Revises: 3516aab4ecf9
Create Date: 2026-01-24 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c1d2f8a9b12'
down_revision: Union[str, Sequence[str], None] = '3516aab4ecf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('passos')}

    with op.batch_alter_table('passos') as batch_op:
        if 'evidence_type' not in columns:
            batch_op.add_column(sa.Column('evidence_type', sa.String(length=20), nullable=True))
        if 'evidence_filename' not in columns:
            batch_op.add_column(sa.Column('evidence_filename', sa.String(length=255), nullable=True))
        if 'evidence_caption' not in columns:
            batch_op.add_column(sa.Column('evidence_caption', sa.Text(), nullable=True))
        if 'evidence_uploaded_at' not in columns:
            batch_op.add_column(sa.Column('evidence_uploaded_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('passos')}

    with op.batch_alter_table('passos') as batch_op:
        if 'evidence_uploaded_at' in columns:
            batch_op.drop_column('evidence_uploaded_at')
        if 'evidence_caption' in columns:
            batch_op.drop_column('evidence_caption')
        if 'evidence_filename' in columns:
            batch_op.drop_column('evidence_filename')
        if 'evidence_type' in columns:
            batch_op.drop_column('evidence_type')
