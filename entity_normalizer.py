from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Perigo
from text_normalizer import normalize_text


def normalized_key(value: str | None) -> str:
    if not value:
        return ""
    normalized = normalize_text(value, keep_newlines=False, origin="entity_normalizer", field=None)
    if not normalized:
        return ""
    return normalized.strip().lower()


def build_hazard_lookup(hazards: Iterable[Perigo]) -> dict[str, Perigo]:
    lookup: dict[str, Perigo] = {}
    for hazard in hazards:
        key = normalized_key(hazard.perigo)
        if not key:
            continue
        lookup[key] = hazard
    return lookup


def load_hazard_lookup(db: Session) -> tuple[list[Perigo], dict[str, Perigo]]:
    hazards = db.execute(select(Perigo)).scalars().all()
    return hazards, build_hazard_lookup(hazards)


def normalize_hazard_list(
    values: Iterable[str] | None,
    *,
    lookup: dict[str, Perigo] | None = None,
    origin: str | None,
    field: str | None,
) -> list[str]:
    if not values:
        return []
    lookup = lookup or {}
    seen: set[str] = set()
    normalized: list[str] = []
    for idx, raw in enumerate(values):
        text = normalize_text(raw, keep_newlines=False, origin=origin, field=f"{field}[{idx}]" if field else None)
        if not text:
            continue
        key = normalized_key(text)
        candidate = lookup.get(key).perigo if key and key in lookup else text
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized
