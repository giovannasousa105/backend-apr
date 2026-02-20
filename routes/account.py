from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from auth import get_current_user, get_db
from models import APR, Company, User
from plan_utils import get_plan_tier, normalize_plan_name
import schemas

router = APIRouter(prefix="/v1/account", tags=["Account"])


def _count_active_aprs(db: Session, company_id: int | None) -> int:
    if not company_id:
        return 0
    stmt = (
        select(func.count())
        .select_from(APR)
        .where(
            APR.company_id == company_id,
            func.lower(APR.status).notin_(("arquivado", "archived")),
        )
    )
    return db.execute(stmt).scalar_one()


@router.get("/plan", response_model=schemas.PlanSummary)
def obter_plano(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.get(Company, current_user.company_id) if current_user.company_id else None
    plan_name = normalize_plan_name(company.plan_name if company else None)
    plan_tier = get_plan_tier(plan_name)
    company_id = company.id if company else current_user.company_id
    active_aprs = _count_active_aprs(db, company_id)

    return {
        "name": plan_name,
        "limits": asdict(plan_tier.limits),
        "features": asdict(plan_tier.features),
        "usage": {
            "active_aprs": active_aprs,
            "active_aprs_limit": plan_tier.limits.max_active_aprs,
        },
    }


@router.get("/metrics", response_model=schemas.AccountMetrics)
def obter_metricas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.get(Company, current_user.company_id) if current_user.company_id else None
    if not company:
        return {
            "company_id": 0,
            "company_name": None,
            "company_plan": "free",
            "users_total": 0,
            "users_active": 0,
            "aprs_total": 0,
            "aprs_active": 0,
            "aprs_created_30d": 0,
        }

    users_total = db.execute(
        select(func.count()).select_from(User).where(User.company_id == company.id)
    ).scalar_one()
    users_active = db.execute(
        select(func.count()).select_from(User).where(
            User.company_id == company.id,
            User.is_active.is_(True),
        )
    ).scalar_one()
    aprs_total = db.execute(
        select(func.count()).select_from(APR).where(APR.company_id == company.id)
    ).scalar_one()
    aprs_active = _count_active_aprs(db, company.id)
    created_since = datetime.utcnow() - timedelta(days=30)
    aprs_created_30d = db.execute(
        select(func.count()).select_from(APR).where(
            APR.company_id == company.id,
            APR.criado_em >= created_since,
        )
    ).scalar_one()

    return {
        "company_id": company.id,
        "company_name": company.name,
        "company_plan": normalize_plan_name(company.plan_name),
        "users_total": users_total,
        "users_active": users_active,
        "aprs_total": aprs_total,
        "aprs_active": aprs_active,
        "aprs_created_30d": aprs_created_30d,
    }
