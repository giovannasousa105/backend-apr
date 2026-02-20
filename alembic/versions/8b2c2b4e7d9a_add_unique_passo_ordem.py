"""add unique constraint for passos ordem per apr

Revision ID: 8b2c2b4e7d9a
Revises: 2fd592cafc5c
Create Date: 2026-01-23 09:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b2c2b4e7d9a"
down_revision: Union[str, Sequence[str], None] = "2fd592cafc5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("passos") as batch_op:
        batch_op.create_unique_constraint(
            "uq_passo_apr_ordem",
            ["apr_id", "ordem"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("passos") as batch_op:
        batch_op.drop_constraint("uq_passo_apr_ordem", type_="unique")
