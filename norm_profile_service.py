from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import APR, NormFramework, NormProfile, NormProfileEvent

SCOPE_COMPANY = "company"
SCOPE_CONTRACT = "contract"
SCOPE_UNIT = "unit"
VALID_SCOPE_TYPES = {SCOPE_COMPANY, SCOPE_CONTRACT, SCOPE_UNIT}

BASE_FRAMEWORK_ID = "NR_BR"
DEFAULT_ENGINE_MODE = "NR_BR"
NORM_ENGINE_VERSION = "norm-engine-v1"

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


def _flag_enabled(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, "true" if default else "false")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


FF_OPTIONAL_FRAMEWORKS_ENABLED = _flag_enabled("FF_OPTIONAL_FRAMEWORKS_ENABLED", True)
FF_RISK_ENGINE_PROFILE_MODE = _flag_enabled("FF_RISK_ENGINE_PROFILE_MODE", True)
FF_APR_PROFILE_SNAPSHOT = _flag_enabled("FF_APR_PROFILE_SNAPSHOT", True)


def _safe_scope_id(value: str | int | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_scope_type(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in VALID_SCOPE_TYPES:
        return raw
    raise ValueError("scope_type invalido")


def build_risk_engine_mode(optional_framework_ids: list[str]) -> str:
    if not FF_RISK_ENGINE_PROFILE_MODE:
        return DEFAULT_ENGINE_MODE
    normalized = [item.strip().upper() for item in optional_framework_ids if str(item).strip()]
    if not normalized:
        return DEFAULT_ENGINE_MODE
    return f"{BASE_FRAMEWORK_ID}_PLUS_" + "_".join(sorted(set(normalized)))


def ensure_framework_catalog(db: Session) -> None:
    existing = {
        item.id: item
        for item in db.execute(select(NormFramework)).scalars().all()
    }
    changed = False
    for raw in DEFAULT_FRAMEWORKS:
        row = existing.get(raw["id"])
        if row is None:
            db.add(NormFramework(**raw))
            changed = True
            continue
        for field in ("type", "name", "description", "country_scope", "is_base", "is_enabled_global"):
            new_value = raw[field]
            if getattr(row, field) != new_value:
                setattr(row, field, new_value)
                changed = True
    if changed:
        db.flush()


def _list_enabled_framework_ids(db: Session) -> set[str]:
    rows = db.execute(
        select(NormFramework.id).where(NormFramework.is_enabled_global.is_(True))
    ).all()
    return {str(row[0]) for row in rows}


def sanitize_optional_framework_ids(db: Session, values: list[str] | None) -> list[str]:
    if not FF_OPTIONAL_FRAMEWORKS_ENABLED:
        return []
    if not values:
        return []
    enabled = _list_enabled_framework_ids(db)
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item).strip()
        if not value or value == BASE_FRAMEWORK_ID or value in seen:
            continue
        if value not in enabled:
            continue
        seen.add(value)
        out.append(value)
    return out


def _serialize_framework_row(framework: NormFramework | None) -> dict[str, Any]:
    if framework is None:
        return {"id": BASE_FRAMEWORK_ID, "type": "NR", "name": "NR base"}
    return {
        "id": framework.id,
        "type": framework.type,
        "name": framework.name,
    }


def serialize_norm_profile(db: Session, profile: NormProfile) -> dict[str, Any]:
    ensure_framework_catalog(db)
    frameworks = {
        item.id: item
        for item in db.execute(select(NormFramework)).scalars().all()
    }
    optional_ids = profile.optional_framework_ids
    optionals = [
        _serialize_framework_row(frameworks.get(item_id))
        for item_id in optional_ids
    ]
    base_row = frameworks.get(profile.base_framework_id)
    return {
        "profileId": f"np_{profile.id}",
        "id": profile.id,
        "version": profile.version,
        "scopeType": profile.scope_type,
        "scopeId": profile.scope_id,
        "base": _serialize_framework_row(base_row),
        "optionals": optionals,
        "riskEngineMode": profile.risk_engine_mode,
        "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
        "updatedBy": profile.updated_by,
    }


def _get_profile_by_scope(
    db: Session,
    *,
    company_id: int,
    scope_type: str,
    scope_id: str,
) -> NormProfile | None:
    stmt = select(NormProfile).where(
        NormProfile.company_id == company_id,
        NormProfile.scope_type == scope_type,
        NormProfile.scope_id == scope_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_or_create_company_default_profile(
    db: Session,
    *,
    company_id: int,
    actor_user_id: int | None = None,
) -> NormProfile:
    ensure_framework_catalog(db)
    scope_id = str(company_id)
    profile = _get_profile_by_scope(
        db,
        company_id=company_id,
        scope_type=SCOPE_COMPANY,
        scope_id=scope_id,
    )
    if profile is not None:
        return profile

    profile = NormProfile(
        company_id=company_id,
        scope_type=SCOPE_COMPANY,
        scope_id=scope_id,
        base_framework_id=BASE_FRAMEWORK_ID,
        optional_framework_ids=[],
        risk_engine_mode=DEFAULT_ENGINE_MODE,
        version=1,
        updated_by=actor_user_id,
    )
    db.add(profile)
    db.flush()
    db.add(
        NormProfileEvent(
            company_id=company_id,
            profile_id=profile.id,
            event="created",
            payload=json.dumps({"scope_type": SCOPE_COMPANY, "scope_id": scope_id}, ensure_ascii=False),
            created_by=actor_user_id,
        )
    )
    db.flush()
    return profile


def resolve_norm_profile(
    db: Session,
    *,
    company_id: int,
    contract_id: str | int | None = None,
    unit_id: str | int | None = None,
    actor_user_id: int | None = None,
) -> tuple[NormProfile, str]:
    ensure_framework_catalog(db)
    contract_scope = _safe_scope_id(contract_id)
    if contract_scope:
        profile = _get_profile_by_scope(
            db,
            company_id=company_id,
            scope_type=SCOPE_CONTRACT,
            scope_id=contract_scope,
        )
        if profile:
            return profile, SCOPE_CONTRACT

    unit_scope = _safe_scope_id(unit_id)
    if unit_scope:
        profile = _get_profile_by_scope(
            db,
            company_id=company_id,
            scope_type=SCOPE_UNIT,
            scope_id=unit_scope,
        )
        if profile:
            return profile, SCOPE_UNIT

    profile = get_or_create_company_default_profile(
        db,
        company_id=company_id,
        actor_user_id=actor_user_id,
    )
    return profile, SCOPE_COMPANY


def upsert_norm_profile(
    db: Session,
    *,
    company_id: int,
    scope_type: str,
    scope_id: str,
    optional_framework_ids: list[str],
    risk_engine_mode: str | None,
    actor_user_id: int | None = None,
) -> NormProfile:
    ensure_framework_catalog(db)
    normalized_scope_type = normalize_scope_type(scope_type)
    normalized_scope_id = _safe_scope_id(scope_id)
    if not normalized_scope_id:
        raise ValueError("scope_id obrigatorio")

    profile = _get_profile_by_scope(
        db,
        company_id=company_id,
        scope_type=normalized_scope_type,
        scope_id=normalized_scope_id,
    )
    if profile is None:
        profile = NormProfile(
            company_id=company_id,
            scope_type=normalized_scope_type,
            scope_id=normalized_scope_id,
            base_framework_id=BASE_FRAMEWORK_ID,
            optional_framework_ids=[],
            risk_engine_mode=DEFAULT_ENGINE_MODE,
            version=1,
            updated_by=actor_user_id,
        )
        db.add(profile)
        db.flush()
        event_name = "created"
    else:
        event_name = "updated"

    optional_ids = sanitize_optional_framework_ids(db, optional_framework_ids)
    computed_mode = risk_engine_mode or build_risk_engine_mode(optional_ids)

    changed = False
    if profile.optional_framework_ids != optional_ids:
        profile.optional_framework_ids = optional_ids
        changed = True
    if profile.risk_engine_mode != computed_mode:
        profile.risk_engine_mode = computed_mode
        changed = True

    if changed:
        profile.version = int(profile.version or 0) + 1
    profile.updated_by = actor_user_id
    profile.updated_at = datetime.utcnow()

    db.add(
        NormProfileEvent(
            company_id=company_id,
            profile_id=profile.id,
            event=event_name,
            payload=json.dumps(
                {
                    "scope_type": profile.scope_type,
                    "scope_id": profile.scope_id,
                    "optional_framework_ids": optional_ids,
                    "risk_engine_mode": profile.risk_engine_mode,
                    "version": profile.version,
                },
                ensure_ascii=False,
            ),
            created_by=actor_user_id,
        )
    )
    db.flush()
    return profile


def apply_profile_snapshot_to_apr(apr: APR, profile: NormProfile, *, resolved_from: str) -> None:
    if not FF_APR_PROFILE_SNAPSHOT:
        return
    apr.norm_profile_id = profile.id
    apr.norm_profile_version = profile.version
    apr.norm_profile_mode = profile.risk_engine_mode
    apr.norm_profile_snapshot = {
        "profileId": profile.id,
        "version": profile.version,
        "scopeType": profile.scope_type,
        "scopeId": profile.scope_id,
        "resolvedFrom": resolved_from,
        "baseFrameworkId": profile.base_framework_id,
        "optionalFrameworkIds": profile.optional_framework_ids,
        "riskEngineMode": profile.risk_engine_mode,
        "engineVersion": NORM_ENGINE_VERSION,
    }
