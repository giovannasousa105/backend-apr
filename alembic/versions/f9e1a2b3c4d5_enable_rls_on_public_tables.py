"""enable rls on public tables flagged by security advisor

Revision ID: f9e1a2b3c4d5
Revises: caad02512426
Create Date: 2026-03-04 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9e1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "caad02512426"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TARGET_TABLES: tuple[str, ...] = (
    "alembic_version",
    "apr_events",
    "apr_shares",
    "apr_tasks",
    "aprs",
    "companies",
    "epis",
    "invites",
    "norm_frameworks",
    "norm_profile_events",
    "norm_profiles",
    "passos",
    "perigos",
    "risk_items",
    "users",
)


def _existing_public_tables(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names(schema="public"))


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_public_tables(bind)
    for table_name in _TARGET_TABLES:
        if table_name in existing:
            op.execute(sa.text(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY'))


def downgrade() -> None:
    bind = op.get_bind()
    existing = _existing_public_tables(bind)
    for table_name in _TARGET_TABLES:
        if table_name in existing:
            op.execute(sa.text(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY'))
