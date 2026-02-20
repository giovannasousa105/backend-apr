from __future__ import annotations

from typing import Iterable


ROLE_ADMIN = "admin"
ROLE_TECNICO = "tecnico"
ROLE_VISUALIZADOR = "visualizador"

ROLE_ALIASES = {
    "user": ROLE_TECNICO,
    "técnico": ROLE_TECNICO,
    "tecnico": ROLE_TECNICO,
    "viewer": ROLE_VISUALIZADOR,
}

VALID_ROLES = {ROLE_ADMIN, ROLE_TECNICO, ROLE_VISUALIZADOR}
WRITE_ROLES = {ROLE_ADMIN, ROLE_TECNICO}


def normalize_role(value: str | None, default: str = ROLE_TECNICO) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return default
    return ROLE_ALIASES.get(raw, raw)


def role_in(role: str | None, allowed: Iterable[str]) -> bool:
    return normalize_role(role, default="") in set(allowed)


def can_write(role: str | None) -> bool:
    return role_in(role, WRITE_ROLES)


def is_admin(role: str | None) -> bool:
    return normalize_role(role) == ROLE_ADMIN
