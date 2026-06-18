"""add norm profiles and apr profile snapshot

Revision ID: 0f9e8d7c6b5a
Revises: f7a8b9c0d1e2
Create Date: 2026-02-26 10:10:00.000000
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f9e8d7c6b5a"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_FRAMEWORKS = [
    {
        "id": "NR_BR",
        "type": "NR",
        "name": "Normas Regulamentadoras (Brasil)",
        "description": "Base obrigatoria para seguranca do trabalho no Brasil.",
        "country_scope": "BR",
        "is_base": True,
        "is_enabled_global": True,
    },
    {
        "id": "ISO_45001",
        "type": "ISO",
        "name": "ISO 45001",
        "description": "Sistema de gestao de saude e seguranca ocupacional.",
        "country_scope": "INTL",
        "is_base": False,
        "is_enabled_global": True,
    },
    {
        "id": "OSHA_1926",
        "type": "OSHA",
        "name": "OSHA 1926",
        "description": "Padrao OSHA para construcao.",
        "country_scope": "US",
        "is_base": False,
        "is_enabled_global": True,
    },
    {
        "id": "ANSI_B11",
        "type": "ANSI",
        "name": "ANSI B11",
        "description": "Seguranca para maquinario industrial.",
        "country_scope": "US",
        "is_base": False,
        "is_enabled_global": True,
    },
]


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "norm_frameworks"):
        op.create_table(
            "norm_frameworks",
            sa.Column("id", sa.String(length=40), primary_key=True),
            sa.Column("type", sa.String(length=20), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("country_scope", sa.String(length=10), nullable=False, server_default="INTL"),
            sa.Column("is_base", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_enabled_global", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_norm_frameworks_type", "norm_frameworks", ["type"], unique=False)

    if not _table_exists(inspector, "norm_profiles"):
        op.create_table(
            "norm_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("scope_type", sa.String(length=20), nullable=False),
            sa.Column("scope_id", sa.String(length=64), nullable=False),
            sa.Column("base_framework_id", sa.String(length=40), nullable=False),
            sa.Column("optional_framework_ids", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("risk_engine_mode", sa.String(length=60), nullable=False, server_default="NR_BR"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["base_framework_id"], ["norm_frameworks.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("company_id", "scope_type", "scope_id", name="uq_norm_profile_scope"),
        )
        op.create_index("ix_norm_profiles_company_id", "norm_profiles", ["company_id"], unique=False)
        op.create_index("ix_norm_profiles_scope_type", "norm_profiles", ["scope_type"], unique=False)
        op.create_index("ix_norm_profiles_scope_id", "norm_profiles", ["scope_id"], unique=False)
        op.create_index("ix_norm_profiles_updated_by", "norm_profiles", ["updated_by"], unique=False)

    if not _table_exists(inspector, "norm_profile_events"):
        op.create_table(
            "norm_profile_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("profile_id", sa.Integer(), nullable=False),
            sa.Column("event", sa.String(length=40), nullable=False, server_default="updated"),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["profile_id"], ["norm_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_norm_profile_events_company_id", "norm_profile_events", ["company_id"], unique=False)
        op.create_index("ix_norm_profile_events_profile_id", "norm_profile_events", ["profile_id"], unique=False)
        op.create_index("ix_norm_profile_events_created_by", "norm_profile_events", ["created_by"], unique=False)

    inspector = sa.inspect(bind)
    apr_columns = {col["name"] for col in inspector.get_columns("aprs")}
    with op.batch_alter_table("aprs") as batch_op:
        if "contract_id" not in apr_columns:
            batch_op.add_column(sa.Column("contract_id", sa.String(length=64), nullable=True))
        if "unit_id" not in apr_columns:
            batch_op.add_column(sa.Column("unit_id", sa.String(length=64), nullable=True))
        if "norm_profile_id" not in apr_columns:
            batch_op.add_column(sa.Column("norm_profile_id", sa.Integer(), nullable=True))
        if "norm_profile_version" not in apr_columns:
            batch_op.add_column(sa.Column("norm_profile_version", sa.Integer(), nullable=True))
        if "norm_profile_mode" not in apr_columns:
            batch_op.add_column(sa.Column("norm_profile_mode", sa.String(length=60), nullable=True))
        if "norm_profile_snapshot" not in apr_columns:
            batch_op.add_column(sa.Column("norm_profile_snapshot", sa.Text(), nullable=True))

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "aprs", "ix_aprs_contract_id"):
        op.create_index("ix_aprs_contract_id", "aprs", ["contract_id"], unique=False)
    if not _index_exists(inspector, "aprs", "ix_aprs_unit_id"):
        op.create_index("ix_aprs_unit_id", "aprs", ["unit_id"], unique=False)
    if not _index_exists(inspector, "aprs", "ix_aprs_norm_profile_id"):
        op.create_index("ix_aprs_norm_profile_id", "aprs", ["norm_profile_id"], unique=False)

    fks = inspector.get_foreign_keys("aprs")
    fk_names = {fk.get("name") for fk in fks if fk.get("name")}
    if "fk_aprs_norm_profile_id" not in fk_names:
        with op.batch_alter_table("aprs") as batch_op:
            batch_op.create_foreign_key(
                "fk_aprs_norm_profile_id",
                "norm_profiles",
                ["norm_profile_id"],
                ["id"],
                ondelete="SET NULL",
            )

    for fw in DEFAULT_FRAMEWORKS:
        exists = bind.execute(
            sa.text("SELECT 1 FROM norm_frameworks WHERE id = :id"),
            {"id": fw["id"]},
        ).first()
        if exists:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO norm_frameworks
                (id, type, name, description, country_scope, is_base, is_enabled_global, created_at, updated_at)
                VALUES
                (:id, :type, :name, :description, :country_scope, :is_base, :is_enabled_global, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            fw,
        )

    company_rows = bind.execute(sa.text("SELECT id FROM companies")).fetchall()
    for row in company_rows:
        company_id = int(row[0])
        existing = bind.execute(
            sa.text(
                """
                SELECT id FROM norm_profiles
                WHERE company_id = :company_id
                  AND scope_type = 'company'
                  AND scope_id = :scope_id
                """
            ),
            {"company_id": company_id, "scope_id": str(company_id)},
        ).first()
        if existing:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO norm_profiles
                (company_id, scope_type, scope_id, base_framework_id, optional_framework_ids, risk_engine_mode, version, created_at, updated_at)
                VALUES
                (:company_id, 'company', :scope_id, 'NR_BR', '[]', 'NR_BR', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"company_id": company_id, "scope_id": str(company_id)},
        )

    apr_rows = bind.execute(
        sa.text(
            """
            SELECT id, company_id
            FROM aprs
            WHERE company_id IS NOT NULL AND norm_profile_id IS NULL
            """
        )
    ).fetchall()
    for row in apr_rows:
        apr_id = int(row[0])
        company_id = int(row[1])
        profile_row = bind.execute(
            sa.text(
                """
                SELECT id, version, risk_engine_mode
                FROM norm_profiles
                WHERE company_id = :company_id
                  AND scope_type = 'company'
                  AND scope_id = :scope_id
                LIMIT 1
                """
            ),
            {"company_id": company_id, "scope_id": str(company_id)},
        ).first()
        if not profile_row:
            continue
        snapshot = {
            "profileId": int(profile_row[0]),
            "version": int(profile_row[1] or 1),
            "scopeType": "company",
            "scopeId": str(company_id),
            "resolvedFrom": "company",
            "baseFrameworkId": "NR_BR",
            "optionalFrameworkIds": [],
            "riskEngineMode": str(profile_row[2] or "NR_BR"),
            "engineVersion": "norm-engine-v1",
        }
        bind.execute(
            sa.text(
                """
                UPDATE aprs
                SET norm_profile_id = :profile_id,
                    norm_profile_version = :profile_version,
                    norm_profile_mode = :mode,
                    norm_profile_snapshot = :snapshot
                WHERE id = :apr_id
                """
            ),
            {
                "profile_id": int(profile_row[0]),
                "profile_version": int(profile_row[1] or 1),
                "mode": str(profile_row[2] or "NR_BR"),
                "snapshot": json.dumps(snapshot, ensure_ascii=False),
                "apr_id": apr_id,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "aprs"):
        with op.batch_alter_table("aprs") as batch_op:
            fks = inspector.get_foreign_keys("aprs")
            fk_names = {fk.get("name") for fk in fks if fk.get("name")}
            if "fk_aprs_norm_profile_id" in fk_names:
                batch_op.drop_constraint("fk_aprs_norm_profile_id", type_="foreignkey")
            apr_columns = {col["name"] for col in inspector.get_columns("aprs")}
            if "norm_profile_snapshot" in apr_columns:
                batch_op.drop_column("norm_profile_snapshot")
            if "norm_profile_mode" in apr_columns:
                batch_op.drop_column("norm_profile_mode")
            if "norm_profile_version" in apr_columns:
                batch_op.drop_column("norm_profile_version")
            if "norm_profile_id" in apr_columns:
                batch_op.drop_column("norm_profile_id")
            if "unit_id" in apr_columns:
                batch_op.drop_column("unit_id")
            if "contract_id" in apr_columns:
                batch_op.drop_column("contract_id")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "aprs"):
        if _index_exists(inspector, "aprs", "ix_aprs_norm_profile_id"):
            op.drop_index("ix_aprs_norm_profile_id", table_name="aprs")
        if _index_exists(inspector, "aprs", "ix_aprs_unit_id"):
            op.drop_index("ix_aprs_unit_id", table_name="aprs")
        if _index_exists(inspector, "aprs", "ix_aprs_contract_id"):
            op.drop_index("ix_aprs_contract_id", table_name="aprs")

    if _table_exists(inspector, "norm_profile_events"):
        op.drop_table("norm_profile_events")
    if _table_exists(inspector, "norm_profiles"):
        op.drop_table("norm_profiles")
    if _table_exists(inspector, "norm_frameworks"):
        op.drop_table("norm_frameworks")
