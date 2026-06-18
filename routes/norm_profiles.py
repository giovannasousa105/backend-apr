from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

import schemas
from api_errors import ApiError
from auth import get_current_user, require_admin
from database import get_db
from models import NormFramework, NormProfile, User
from norm_profile_service import (
    resolve_norm_profile,
    serialize_norm_profile,
    upsert_norm_profile,
)

router = APIRouter(prefix="/v1", tags=["norms"])



@router.get("/norm-frameworks", response_model=list[schemas.NormFrameworkOut])
def list_norm_frameworks(
    only_enabled: bool = Query(default=True),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    stmt = select(NormFramework)
    if only_enabled:
        stmt = stmt.where(NormFramework.is_enabled_global.is_(True))
    stmt = stmt.order_by(NormFramework.is_base.desc(), NormFramework.type.asc(), NormFramework.id.asc())
    return db.execute(stmt).scalars().all()


@router.get("/norm-profiles", response_model=list[schemas.NormProfileResolvedOut])
def list_norm_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    if not company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")
    resolve_norm_profile(
        db,
        company_id=int(company_id),
        actor_user_id=current_user.id,
    )
    db.flush()
    rows = db.execute(
        select(NormProfile).where(NormProfile.company_id == company_id).order_by(NormProfile.scope_type.asc(), NormProfile.scope_id.asc())
    ).scalars().all()
    return [serialize_norm_profile(db, row) for row in rows]


@router.get("/norm-profiles/resolve", response_model=schemas.NormProfileResolvedOut)
def resolve_norm_profile_route(
    companyId: int | None = Query(default=None),
    contractId: str | None = Query(default=None),
    unitId: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_company = current_user.company_id
    if not current_company:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")
    if companyId is not None and int(companyId) != int(current_company):
        raise ApiError(status_code=403, code="forbidden", message="Acesso fora da empresa", field="companyId")

    profile, resolved_from = resolve_norm_profile(
        db,
        company_id=int(current_company),
        contract_id=contractId,
        unit_id=unitId,
        actor_user_id=current_user.id,
    )
    db.commit()
    payload = serialize_norm_profile(db, profile)
    payload["resolvedFrom"] = resolved_from
    return payload


@router.post("/norm-profiles", response_model=schemas.NormProfileResolvedOut)
def create_or_update_norm_profile(
    payload: schemas.NormProfileUpsert,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    company_id = admin.company_id
    if not company_id:
        raise ApiError(status_code=403, code="forbidden", message="Admin sem empresa vinculada", field="company_id")
    profile = upsert_norm_profile(
        db,
        company_id=int(company_id),
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        optional_framework_ids=payload.optional_framework_ids,
        risk_engine_mode=payload.risk_engine_mode,
        actor_user_id=admin.id,
    )
    db.commit()
    return serialize_norm_profile(db, profile)


@router.put("/norm-profiles/{profile_id}", response_model=schemas.NormProfileResolvedOut)
def update_norm_profile(
    profile_id: int,
    payload: schemas.NormProfileUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    company_id = admin.company_id
    if not company_id:
        raise ApiError(status_code=403, code="forbidden", message="Admin sem empresa vinculada", field="company_id")

    profile = db.get(NormProfile, profile_id)
    if not profile or profile.company_id != company_id:
        raise ApiError(status_code=404, code="not_found", message="Perfil normativo nao encontrado", field="profile_id")

    optional_ids = payload.optional_framework_ids
    if optional_ids is None:
        optional_ids = profile.optional_framework_ids
    engine_mode = payload.risk_engine_mode or profile.risk_engine_mode

    profile = upsert_norm_profile(
        db,
        company_id=int(company_id),
        scope_type=profile.scope_type,
        scope_id=profile.scope_id,
        optional_framework_ids=optional_ids,
        risk_engine_mode=engine_mode,
        actor_user_id=admin.id,
    )
    db.commit()
    return serialize_norm_profile(db, profile)



