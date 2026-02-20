from __future__ import annotations

_STATUS_MAP = {
    "rascunho": "draft",
    "draft": "draft",
    "enviado": "submitted",
    "submitted": "submitted",
    "aprovado": "approved",
    "approved": "approved",
    "reprovado": "rejected",
    "rejected": "rejected",
    "final": "final",
    "arquivado": "archived",
    "archived": "archived",
}


def normalize_status(value: str | None) -> str:
    if not value:
        return "draft"
    normalized = str(value).strip().lower()
    return _STATUS_MAP.get(normalized, normalized)


def is_final_status(value: str | None) -> bool:
    return normalize_status(value) in {"approved", "final"}


def is_archived_status(value: str | None) -> bool:
    return normalize_status(value) == "archived"
