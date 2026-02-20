from __future__ import annotations

from datetime import datetime
import re
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from entity_normalizer import (
    load_hazard_lookup,
    normalize_hazard_list,
    normalized_key as _norm_key,
)
from excel_contract import RISK_MATRIX
from models import Passo, Perigo, RiskItem
from text_normalizer import normalize_text, normalize_list

_LIST_RE = re.compile(r";")


def _split_list(value, *, origin: str, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in normalize_list(value, origin=origin, field=field) if v]
    text = normalize_text(value, keep_newlines=False, origin=origin, field=field) or ""
    if not text:
        return []
    parts = _LIST_RE.split(text)
    return [
        normalize_text(p, keep_newlines=False, origin=origin, field=field) or ""
        for p in parts
        if str(p).strip()
    ]



def _safe_int(value) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except Exception:
        return 0


def _matrix_limits() -> tuple[int, int, int, int]:
    prob = RISK_MATRIX.get("probability", {})
    sev = RISK_MATRIX.get("severity", {})
    prob_min = _safe_int(prob.get("min")) or 1
    prob_max = _safe_int(prob.get("max")) or 5
    sev_min = _safe_int(sev.get("min")) or 1
    sev_max = _safe_int(sev.get("max")) or 5
    return prob_min, prob_max, sev_min, sev_max


def _score_to_level(score: int) -> str | None:
    bands = RISK_MATRIX.get("bands", [])
    for band in bands:
        band_min = _safe_int(band.get("min"))
        band_max = _safe_int(band.get("max"))
        level = band.get("level")
        if band_min <= score <= band_max and level is not None:
            return str(level)
    return None


def compute_risk_score(probability: int, severity: int) -> tuple[int, str]:
    prob_min, prob_max, sev_min, sev_max = _matrix_limits()
    probability = _safe_int(probability)
    severity = _safe_int(severity)
    if probability < prob_min or probability > prob_max:
        return 0, "invalid"
    if severity < sev_min or severity > sev_max:
        return 0, "invalid"

    score = probability * severity
    level = _score_to_level(score)
    if not level:
        return score, "invalid"
    return score, level


def is_risk_item_valid(item: RiskItem) -> bool:
    if item is None:
        return False
    score, level = compute_risk_score(item.probability, item.severity)
    if level == "invalid":
        return False
    if item.score != score:
        return False
    if item.risk_level != level:
        return False
    return True


def has_invalid_risk_items(items: Iterable[RiskItem]) -> bool:
    return any(not is_risk_item_valid(item) for item in items)


def _resolve_hazard_id(
    risk_description: str,
    hazards: list[str],
    hazard_lookup: dict[str, Perigo],
) -> int | None:
    if not hazards:
        return None

    known = []
    for hazard in hazards:
        key = _norm_key(hazard)
        if not key:
            continue
        perigo = hazard_lookup.get(key)
        if perigo:
            known.append((hazard, perigo))

    if not known:
        return None
    if len(known) == 1:
        return known[0][1].id

    risk_lower = (risk_description or "").lower()
    matches = [p.id for name, p in known if name and name.lower() in risk_lower]
    if len(matches) == 1:
        return matches[0]
    return None


def rebuild_risk_items_for_apr(db: Session, apr_id: int) -> dict[str, int]:
    passos = (
        db.execute(select(Passo).where(Passo.apr_id == apr_id).order_by(Passo.ordem))
        .scalars()
        .all()
    )
    hazards, hazard_lookup = load_hazard_lookup(db)
    hazard_by_id = {h.id: h for h in hazards}

    db.execute(delete(RiskItem).where(RiskItem.apr_id == apr_id))

    created = 0
    invalid = 0

    for passo in passos:
        risks = _split_list(passo.riscos, origin="user", field="riscos")
        raw_hazards = _split_list(passo.perigos, origin="user", field="perigos")
        hazards_list = normalize_hazard_list(
            raw_hazards, lookup=hazard_lookup, origin="user", field="perigos"
        )

        for risk_description in risks:
            if not risk_description:
                continue

            hazard_id = _resolve_hazard_id(risk_description, hazards_list, hazard_lookup)
            hazard = hazard_by_id.get(hazard_id) if hazard_id else None
            raw_probability = getattr(hazard, "default_probability", None) if hazard else None
            raw_severity = getattr(hazard, "default_severity", None) if hazard else None
            probability = _safe_int(raw_probability)
            severity = _safe_int(raw_severity)
            score, level = compute_risk_score(probability, severity)
            if level == "invalid":
                invalid += 1

            db.add(
                RiskItem(
                    apr_id=apr_id,
                    company_id=passo.company_id,
                    step_id=passo.id,
                    hazard_id=hazard_id,
                    risk_description=risk_description,
                    probability=probability,
                    severity=severity,
                    score=score,
                    risk_level=level,
                    updated_at=datetime.utcnow(),
                )
            )
            created += 1

    db.flush()
    return {"created": created, "invalid": invalid}


def list_risk_items_for_apr(db: Session, apr_id: int) -> list[RiskItem]:
    return (
        db.execute(select(RiskItem).where(RiskItem.apr_id == apr_id).order_by(RiskItem.id))
        .scalars()
        .all()
    )
