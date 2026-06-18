"""add security audit hash chain and append-only guard

Revision ID: d8f9a0b1c2d3
Revises: c7d8e9f0a1b2
Create Date: 2026-03-08 14:10:00.000000
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names(schema="public"))


def _column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {str(item["name"]) for item in inspector.get_columns(table_name, schema="public")}


def _index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {str(item["name"]) for item in inspector.get_indexes(table_name, schema="public")}


def _normalize_payload(raw_payload: str | None) -> str:
    if not raw_payload:
        return "{}"
    try:
        decoded = json.loads(raw_payload)
    except Exception:
        return json.dumps({"_raw": str(raw_payload)}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(decoded, dict):
        return json.dumps(decoded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return json.dumps({"_raw": decoded}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _entry_hash(
    *,
    company_id: int | None,
    user_id: int | None,
    session_id: int | None,
    event: str | None,
    payload: str,
    ip_address: str | None,
    user_agent: str | None,
    created_at: datetime | None,
    previous_hash: str | None,
) -> str:
    created_value = (created_at or datetime.utcnow()).replace(tzinfo=None).isoformat(timespec="microseconds")
    material = "\n".join(
        [
            str(company_id or ""),
            str(user_id or ""),
            str(session_id or ""),
            str((event or "unknown").strip() or "unknown"),
            payload,
            str((ip_address or "").strip()),
            str((user_agent or "").strip()),
            created_value,
            str(previous_hash or ""),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _backfill_hash_chain(bind) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id, company_id, user_id, session_id, event, payload, ip_address, user_agent, created_at
            FROM public.security_audit_events
            ORDER BY company_id ASC, created_at ASC, id ASC
            """
        )
    ).mappings().all()

    previous_by_company: dict[int, str | None] = {}
    for row in rows:
        company_id = int(row["company_id"])
        previous_hash = previous_by_company.get(company_id)
        payload = _normalize_payload(row["payload"])
        event_hash = _entry_hash(
            company_id=company_id,
            user_id=row["user_id"],
            session_id=row["session_id"],
            event=row["event"],
            payload=payload,
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            created_at=row["created_at"],
            previous_hash=previous_hash,
        )
        bind.execute(
            sa.text(
                """
                UPDATE public.security_audit_events
                SET previous_hash = :previous_hash,
                    event_hash = :event_hash
                WHERE id = :event_id
                """
            ),
            {
                "previous_hash": previous_hash,
                "event_hash": event_hash,
                "event_id": int(row["id"]),
            },
        )
        previous_by_company[company_id] = event_hash


def _create_append_only_trigger(bind) -> None:
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION public.prevent_security_audit_events_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'security_audit_events is append-only';
            END;
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS trg_security_audit_events_no_mutation
            ON public.security_audit_events
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_security_audit_events_no_mutation
            BEFORE UPDATE OR DELETE ON public.security_audit_events
            FOR EACH ROW
            EXECUTE FUNCTION public.prevent_security_audit_events_mutation()
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "security_audit_events"):
        return

    columns = _column_names(bind, "security_audit_events")
    if "previous_hash" not in columns:
        op.add_column("security_audit_events", sa.Column("previous_hash", sa.String(length=64), nullable=True))
    if "event_hash" not in columns:
        op.add_column("security_audit_events", sa.Column("event_hash", sa.String(length=64), nullable=True))

    _backfill_hash_chain(bind)

    with op.batch_alter_table("security_audit_events") as batch_op:
        batch_op.alter_column("event_hash", existing_type=sa.String(length=64), nullable=False)

    index_names = _index_names(bind, "security_audit_events")
    if "ix_security_audit_events_event_hash" not in index_names:
        op.create_index(
            "ix_security_audit_events_event_hash",
            "security_audit_events",
            ["event_hash"],
            unique=True,
        )

    _create_append_only_trigger(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "security_audit_events"):
        return

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DROP TRIGGER IF EXISTS trg_security_audit_events_no_mutation
                ON public.security_audit_events
                """
            )
        )
        op.execute(sa.text("DROP FUNCTION IF EXISTS public.prevent_security_audit_events_mutation()"))

    index_names = _index_names(bind, "security_audit_events")
    if "ix_security_audit_events_event_hash" in index_names:
        op.drop_index("ix_security_audit_events_event_hash", table_name="security_audit_events")

    columns = _column_names(bind, "security_audit_events")
    with op.batch_alter_table("security_audit_events") as batch_op:
        if "event_hash" in columns:
            batch_op.drop_column("event_hash")
        if "previous_hash" in columns:
            batch_op.drop_column("previous_hash")
