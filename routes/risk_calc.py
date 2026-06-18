from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import schemas
from api_errors import ApiError
from auth import get_current_user
from database import get_db
from models import APR, NormProfile, RiskItem, User
from norm_profile_service import NORM_ENGINE_VERSION, resolve_norm_profile
from risk_engine import compute_risk_score

router = APIRouter(prefix="/v1/risk", tags=["risk"])



def _level_bucket(score: int) -> str:
    if score <= 5:
        return "baixo"
    if score <= 12:
        return "medio"
    return "alto"


def _assert_apr_access(apr: APR, user: User) -> None:
    if not user.company_id or not apr.company_id or apr.company_id != user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Acesso negado", field="aprId")


@router.post("/calc", response_model=schemas.RiskCalcOut)
def calc_risk(
    payload: schemas.RiskCalcInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    if not company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")

    apr: APR | None = None
    if payload.aprId is not None:
        apr = db.get(APR, payload.aprId)
        if not apr:
            raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="aprId")
        _assert_apr_access(apr, current_user)

    profile: NormProfile | None = None
    if payload.normProfileId is not None:
        profile = db.get(NormProfile, payload.normProfileId)
        if not profile or profile.company_id != company_id:
            raise ApiError(status_code=404, code="not_found", message="Perfil normativo nao encontrado", field="normProfileId")
    elif apr and apr.norm_profile_id:
        profile = db.get(NormProfile, apr.norm_profile_id)
        if profile and profile.company_id != company_id:
            profile = None

    if profile is None:
        profile, _resolved_from = resolve_norm_profile(
            db,
            company_id=int(company_id),
            contract_id=payload.contractId or (apr.contract_id if apr else None),
            unit_id=payload.unitId or (apr.unit_id if apr else None),
            actor_user_id=current_user.id,
        )

    if payload.profileVersion is not None and int(payload.profileVersion) != int(profile.version):
        raise ApiError(
            status_code=409,
            code="profile_version_mismatch",
            message="Versao do perfil normativo divergente",
            field="profileVersion",
        )

    raw_steps = payload.steps
    if not raw_steps and apr is not None:
        apr_items = db.query(RiskItem).filter(RiskItem.apr_id == apr.id).order_by(RiskItem.step_id.asc(), RiskItem.id.asc()).all()
        raw_steps = [
            schemas.RiskCalcStepInput(
                step_order=(idx + 1),
                probability=max(1, min(5, int(item.probability or 1))),
                severity=max(1, min(5, int(item.severity or 1))),
            )
            for idx, item in enumerate(apr_items)
        ]

    if not raw_steps:
        raise ApiError(status_code=400, code="missing_field", message="Informe passos para calcular PxS", field="steps")

    computed_steps: list[schemas.RiskCalcStepOut] = []
    low = medium = high = 0
    max_score = 0

    for step in raw_steps:
        score, level = compute_risk_score(step.probability, step.severity)
        if level == "invalid":
            raise ApiError(status_code=400, code="validation_error", message="PxS invalido em um dos passos", field="steps")
        bucket = _level_bucket(score)
        if bucket == "baixo":
            low += 1
        elif bucket == "medio":
            medium += 1
        else:
            high += 1
        max_score = max(max_score, score)
        computed_steps.append(
            schemas.RiskCalcStepOut(
                stepOrder=step.step_order,
                probability=step.probability,
                severity=step.severity,
                score=score,
                riskLevel=bucket,
            )
        )

    db.commit()
    return schemas.RiskCalcOut(
        aprId=apr.id if apr else payload.aprId,
        normProfileId=profile.id,
        profileVersionUsed=profile.version,
        riskEngineMode=profile.risk_engine_mode,
        engineVersion=NORM_ENGINE_VERSION,
        steps=computed_steps,
        totals=schemas.RiskCalcTotalsOut(
            totalSteps=len(computed_steps),
            baixo=low,
            medio=medium,
            alto=high,
            maxScore=max_score,
        ),
    )




