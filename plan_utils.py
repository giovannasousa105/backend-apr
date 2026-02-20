from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast


PlanName = Literal["free", "pro", "enterprise"]
DEFAULT_PLAN: PlanName = "free"


@dataclass(frozen=True)
class PlanLimits:
    max_active_aprs: int | None
    ai_generations_per_month: int | None
    evidence_per_step: int | None


@dataclass(frozen=True)
class PlanFeatures:
    pdf_logo: bool
    pdf_watermark: bool
    template_library: bool
    checklist_nr: bool
    history: bool
    duplicate_apr: bool
    ai_assistant: bool


@dataclass(frozen=True)
class PlanTier:
    limits: PlanLimits
    features: PlanFeatures


_PLAN_TIERS: dict[PlanName, PlanTier] = {
    "free": PlanTier(
        limits=PlanLimits(
            max_active_aprs=5,
            ai_generations_per_month=3,
            evidence_per_step=1,
        ),
        features=PlanFeatures(
            pdf_logo=False,
            pdf_watermark=True,
            template_library=False,
            checklist_nr=False,
            history=False,
            duplicate_apr=False,
            ai_assistant=True,
        ),
    ),
    "pro": PlanTier(
        limits=PlanLimits(
            max_active_aprs=None,
            ai_generations_per_month=100,
            evidence_per_step=None,
        ),
        features=PlanFeatures(
            pdf_logo=True,
            pdf_watermark=False,
            template_library=True,
            checklist_nr=True,
            history=True,
            duplicate_apr=True,
            ai_assistant=True,
        ),
    ),
    "enterprise": PlanTier(
        limits=PlanLimits(
            max_active_aprs=None,
            ai_generations_per_month=None,
            evidence_per_step=None,
        ),
        features=PlanFeatures(
            pdf_logo=True,
            pdf_watermark=False,
            template_library=True,
            checklist_nr=True,
            history=True,
            duplicate_apr=True,
            ai_assistant=True,
        ),
    ),
}


def normalize_plan_name(value: str | None) -> PlanName:
    if not value:
        return DEFAULT_PLAN
    candidate = str(value).strip().lower()
    if not candidate:
        return DEFAULT_PLAN
    if candidate not in _PLAN_TIERS:
        return DEFAULT_PLAN
    return cast(PlanName, candidate)


def get_plan_tier(plan_name: str | None) -> PlanTier:
    normalized = normalize_plan_name(plan_name)
    return _PLAN_TIERS[normalized]
