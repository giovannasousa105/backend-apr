from __future__ import annotations

from typing import Iterable


ROLE_ADMIN = "admin"
ROLE_TECNICO = "tecnico"
ROLE_VISUALIZADOR = "visualizador"
ROLE_OPERADOR = "operador"
ROLE_APROVADOR = "aprovador"
ROLE_GESTOR_SEGURANCA = "gestor_seguranca"

ROLE_ALIASES = {
    "owner": ROLE_ADMIN,
    "dono": ROLE_ADMIN,
    "user": ROLE_TECNICO,
    "tecnico": ROLE_TECNICO,
    "técnico": ROLE_TECNICO,
    "operador": ROLE_OPERADOR,
    "operator": ROLE_OPERADOR,
    "aprovador": ROLE_APROVADOR,
    "approver": ROLE_APROVADOR,
    "gestor": ROLE_GESTOR_SEGURANCA,
    "gestor_seguranca": ROLE_GESTOR_SEGURANCA,
    "gestor-seguranca": ROLE_GESTOR_SEGURANCA,
    "seguranca": ROLE_GESTOR_SEGURANCA,
    "manager": ROLE_GESTOR_SEGURANCA,
    "viewer": ROLE_VISUALIZADOR,
}

VALID_ROLES = {
    ROLE_ADMIN,
    ROLE_TECNICO,
    ROLE_VISUALIZADOR,
    ROLE_OPERADOR,
    ROLE_APROVADOR,
    ROLE_GESTOR_SEGURANCA,
}

WRITE_ROLES = {
    ROLE_ADMIN,
    ROLE_TECNICO,
    ROLE_OPERADOR,
    ROLE_APROVADOR,
    ROLE_GESTOR_SEGURANCA,
}

PERMISSION_MATRIX: dict[str, set[str]] = {
    "apr.create_own": {ROLE_OPERADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN, ROLE_TECNICO},
    "apr.edit_own": {ROLE_OPERADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN, ROLE_TECNICO},
    "apr.manage_hazards_controls": {ROLE_OPERADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN, ROLE_TECNICO},
    "evidence.upload": {
        ROLE_OPERADOR,
        ROLE_APROVADOR,
        ROLE_GESTOR_SEGURANCA,
        ROLE_ADMIN,
        ROLE_TECNICO,
    },
    "approval.decide": {ROLE_APROVADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN},
    "evidence.request": {ROLE_APROVADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN},
    "dashboard.view_wide": {ROLE_GESTOR_SEGURANCA, ROLE_ADMIN},
    "dashboard.view_limited": {
        ROLE_OPERADOR,
        ROLE_APROVADOR,
        ROLE_GESTOR_SEGURANCA,
        ROLE_ADMIN,
        ROLE_TECNICO,
        ROLE_VISUALIZADOR,
    },
    "admin.config": {ROLE_ADMIN},
    "task.manage": {ROLE_APROVADOR, ROLE_GESTOR_SEGURANCA, ROLE_ADMIN},
}


def normalize_role(value: str | None, default: str = ROLE_TECNICO) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return default
    return ROLE_ALIASES.get(raw, raw)


def _policy_role(role: str | None) -> str:
    normalized = normalize_role(role, default="")
    if normalized == ROLE_TECNICO:
        return ROLE_OPERADOR
    return normalized


def role_in(role: str | None, allowed: Iterable[str]) -> bool:
    return normalize_role(role, default="") in set(allowed)


def can_write(role: str | None) -> bool:
    return role_in(role, WRITE_ROLES)


def has_permission(role: str | None, action: str) -> bool:
    allowed = PERMISSION_MATRIX.get(action)
    if not allowed:
        return False
    return _policy_role(role) in allowed


def is_admin(role: str | None) -> bool:
    return normalize_role(role) == ROLE_ADMIN
