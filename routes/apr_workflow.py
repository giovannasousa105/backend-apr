from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import schemas
from api_errors import ApiError
from auth import get_current_user, get_db
from models import APR, APREvent, APRTask, Passo, RiskItem, User
from request_guards import apply_rate_limit, request_identity
from rbac import has_permission, normalize_role
from risk_engine import is_risk_item_valid
from status_utils import normalize_status

router = APIRouter(prefix="/v1", tags=["APR Workflow"])

_STAGES = ("criar", "perigos", "controles", "aprovacao", "execucao", "relatorio")
_STAGE_INDEX = {stage: idx for idx, stage in enumerate(_STAGES)}
_TASK_OPEN_STATUSES = {"open", "in_progress"}
_TASK_DONE_STATUSES = {"done", "canceled"}
_EVENTS_REQUIRING_REASON = {"approval_rejected", "evidence_requested"}


class _AuditPayloadModel(BaseModel):
    timestamp: datetime
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: str = Field(min_length=1)
    reason: str | None = None
    apr_id: int
    stage: str
    step_id: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    actor: dict[str, Any] | None = None


def _normalize_stage(value: str | None, *, default: str = "criar") -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    if normalized not in _STAGES:
        raise ApiError(status_code=422, code="validation_error", message="Etapa invalida", field="stage")
    return normalized


def _safe_stage(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if normalized in _STAGES:
        return normalized
    return None


def _actor_payload(actor: User | None) -> dict[str, Any] | None:
    if not actor:
        return None
    return {
        "id": actor.id,
        "email": actor.email,
        "name": actor.name,
        "role": normalize_role(actor.role),
    }


def _ensure_permission(user: User, action: str) -> None:
    if not has_permission(user.role, action):
        raise ApiError(status_code=403, code="forbidden", message="Permissao insuficiente", field="role")


def _ensure_any_permission(user: User, actions: tuple[str, ...]) -> None:
    if any(has_permission(user.role, action) for action in actions):
        return
    raise ApiError(status_code=403, code="forbidden", message="Permissao insuficiente", field="role")


def _resolve_apr(apr_ref: str, db: Session) -> APR:
    apr = db.execute(select(APR).where(APR.external_id == apr_ref)).scalar_one_or_none()
    if apr:
        return apr
    numeric_id = int(apr_ref) if apr_ref.isdigit() else None
    if numeric_id is not None:
        apr = db.get(APR, numeric_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    return apr


def _ensure_same_company(apr: APR, user: User) -> None:
    if not user.company_id or not apr.company_id or apr.company_id != user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Acesso negado", field="apr_id")


def _is_blank_text(value: str | None) -> bool:
    return not (value or "").strip()


def _count_named_items(items: list[Any]) -> int:
    named = 0
    for item in items:
        if isinstance(item, str) and item.strip():
            named += 1
            continue
        if not isinstance(item, dict):
            continue
        for key in ("name", "label", "hazard", "perigo", "control", "item"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                named += 1
                break
    return named


def _build_matrix_validation(apr: APR, db: Session) -> dict[str, Any]:
    issues: list[str] = []
    hazards = apr.hazards or []
    controls = apr.controls or []
    if not hazards:
        issues.append("Adicione pelo menos 1 perigo na matriz.")
    elif _count_named_items(hazards) == 0:
        issues.append("Preencha o nome de pelo menos 1 perigo na matriz.")
    if not controls:
        issues.append("Adicione pelo menos 1 controle na matriz.")
    elif _count_named_items(controls) == 0:
        issues.append("Preencha o nome de pelo menos 1 controle na matriz.")

    passos = (
        db.execute(select(Passo).where(Passo.apr_id == apr.id).order_by(Passo.ordem))
        .scalars()
        .all()
    )
    if not passos:
        issues.append("Adicione pelo menos 1 passo na atividade.")
    else:
        required_fields = (
            ("descricao", "descricao"),
            ("perigos", "perigos"),
            ("riscos", "consequencias"),
            ("medidas_controle", "salvaguardas"),
            ("epis", "epis"),
            ("normas", "normas/referencias"),
        )
        for passo in passos:
            missing = [
                label
                for attr, label in required_fields
                if _is_blank_text(getattr(passo, attr, None))
            ]
            if missing:
                issues.append(
                    f"Passo {passo.ordem} incompleto: preencha {', '.join(missing)}."
                )

    risk_items = (
        db.execute(select(RiskItem).where(RiskItem.apr_id == apr.id).order_by(RiskItem.id))
        .scalars()
        .all()
    )
    if not risk_items:
        issues.append("Matriz sem riscos calculados.")
    else:
        if passos:
            step_ids_with_risk = {item.step_id for item in risk_items if item.step_id is not None}
            missing_risk_steps = [str(passo.ordem) for passo in passos if passo.id not in step_ids_with_risk]
            if missing_risk_steps:
                issues.append(
                    "Passo(s) sem risco calculado: " + ", ".join(missing_risk_steps) + "."
                )
        blank_description_count = sum(1 for item in risk_items if _is_blank_text(item.risk_description))
        if blank_description_count > 0:
            issues.append(f"Existem {blank_description_count} risco(s) sem descricao.")
        invalid_risk_count = sum(1 for item in risk_items if not is_risk_item_valid(item))
        if invalid_risk_count > 0:
            issues.append(
                f"Existem {invalid_risk_count} risco(s) com PxS invalido. "
                "Probabilidade e severidade devem estar entre 1 e 5."
            )

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "steps_count": len(passos),
        "risk_items_count": len(risk_items),
    }


def _validate_stage_transition(current_stage: str, next_stage: str) -> None:
    current_idx = _STAGE_INDEX.get(current_stage, 0)
    next_idx = _STAGE_INDEX[next_stage]
    if abs(next_idx - current_idx) > 1:
        raise ApiError(
            status_code=422,
            code="invalid_stage_transition",
            message=f"Transicao invalida de {current_stage} para {next_stage}",
            field="stage",
        )


def _append_audit_event(
    db: Session,
    apr: APR,
    action: str,
    *,
    actor: User | None,
    reason: str | None = None,
    stage: str | None = None,
    step_id: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if action in _EVENTS_REQUIRING_REASON and not (reason or "").strip():
        raise ApiError(status_code=422, code="validation_error", message="Motivo obrigatorio", field="reason")

    target_stage = _normalize_stage(stage or apr.current_stage or "criar")
    actor_data = _actor_payload(actor)
    payload_raw = {
        "timestamp": datetime.utcnow(),
        "actor_user_id": actor.id if actor else None,
        "actor_role": normalize_role(actor.role) if actor else None,
        "action": action,
        "reason": reason,
        "apr_id": apr.id,
        "stage": target_stage,
        "step_id": step_id,
        "meta": meta or {},
        "actor": actor_data,
    }

    try:
        payload = _AuditPayloadModel.model_validate(payload_raw)
    except ValidationError as exc:
        raise ApiError(status_code=422, code="validation_error", message=str(exc), field="payload")

    db.add(
        APREvent(
            apr_id=apr.id,
            company_id=apr.company_id,
            event=action,
            payload=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
        )
    )


def _parse_event_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _apr_workflow_identity(request: Request, user: User, resource: str | None = None) -> str:
    principal = str(user.id)
    if resource:
        principal = f"{user.id}:{resource}"
    return request_identity(request, principal)


@router.patch("/aprs/{apr_id}/stage", response_model=schemas.APROut)
def patch_apr_stage(
    apr_id: str,
    payload: schemas.APRStageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_stage_update", _apr_workflow_identity(request, current_user, apr_id), limit=60, window_seconds=60)
    _ensure_permission(current_user, "apr.edit_own")
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    current_stage = _normalize_stage(apr.current_stage or "criar")
    next_stage = _normalize_stage(payload.stage)
    if next_stage == current_stage:
        return apr

    _validate_stage_transition(current_stage, next_stage)
    if next_stage == "aprovacao":
        matrix_validation = _build_matrix_validation(apr, db)
        if not matrix_validation["ready"]:
            issues = matrix_validation.get("issues") or []
            first_issue = str(issues[0]) if issues else "Matriz de risco incompleta."
            raise ApiError(
                status_code=422,
                code="matrix_incomplete",
                message=first_issue,
                field="stage",
            )
    apr.current_stage = next_stage

    _append_audit_event(
        db,
        apr,
        "stage_changed",
        actor=current_user,
        reason=payload.reason,
        stage=next_stage,
        meta={"from": current_stage, "to": next_stage},
    )
    db.commit()
    db.refresh(apr)
    return apr


@router.get("/aprs/{apr_id}/matrix/validate")
def validate_matrix_before_stage(
    apr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_any_permission(current_user, ("apr.edit_own", "approval.decide", "dashboard.view_limited"))
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    matrix_validation = _build_matrix_validation(apr, db)
    return {
        "apr_id": apr.external_id or str(apr.id),
        **matrix_validation,
    }


@router.get("/aprs/{apr_id}/tasks", response_model=schemas.PaginatedAPRTaskOut)
def list_apr_tasks(
    apr_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_permission(current_user, "dashboard.view_limited")
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    limit = min(max(limit, 1), 200)
    base = select(APRTask).where(APRTask.apr_id == apr.id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    items = (
        db.execute(base.order_by(APRTask.created_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/aprs/{apr_id}/tasks", response_model=schemas.APRTaskOut)
def create_apr_task(
    apr_id: str,
    payload: schemas.APRTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_task_create", _apr_workflow_identity(request, current_user, apr_id), limit=30, window_seconds=60)
    _ensure_permission(current_user, "task.manage")
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    task = APRTask(
        apr_id=apr.id,
        company_id=apr.company_id,
        step_id=payload.step_id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        assigned_to_user_id=payload.assigned_to_user_id,
        requested_by_user_id=current_user.id,
        priority=payload.priority,
        status="open",
        due_at=payload.due_at,
        reason=payload.reason,
    )
    db.add(task)
    db.flush()

    _append_audit_event(
        db,
        apr,
        "task_created",
        actor=current_user,
        reason=payload.reason,
        step_id=payload.step_id,
        meta={
            "task_id": task.id,
            "task_type": task.type,
            "priority": task.priority,
            "assigned_to_user_id": task.assigned_to_user_id,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        },
    )
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.APRTaskOut)
def patch_task(
    task_id: int,
    payload: schemas.APRTaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_task_update", _apr_workflow_identity(request, current_user, str(task_id)), limit=60, window_seconds=60)
    task = db.get(APRTask, task_id)
    if not task:
        raise ApiError(status_code=404, code="not_found", message="Task nao encontrada", field="task_id")
    apr = db.get(APR, task.apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_same_company(apr, current_user)

    is_manager = has_permission(current_user.role, "task.manage")
    if not is_manager and task.assigned_to_user_id != current_user.id:
        raise ApiError(status_code=403, code="forbidden", message="Permissao insuficiente", field="task_id")

    updates: dict[str, Any] = {}
    if payload.status is not None:
        task.status = payload.status
        updates["status"] = task.status
    if payload.assigned_to_user_id is not None:
        task.assigned_to_user_id = payload.assigned_to_user_id
        updates["assigned_to_user_id"] = task.assigned_to_user_id
    if payload.priority is not None:
        task.priority = payload.priority
        updates["priority"] = task.priority
    if payload.due_at is not None:
        task.due_at = payload.due_at
        updates["due_at"] = task.due_at.isoformat()
    if payload.reason is not None:
        task.reason = payload.reason
        updates["reason"] = task.reason

    if task.status in _TASK_DONE_STATUSES and task.resolved_at is None:
        task.resolved_at = datetime.utcnow()
    if task.status in _TASK_OPEN_STATUSES:
        task.resolved_at = None

    _append_audit_event(
        db,
        apr,
        "task_updated",
        actor=current_user,
        reason=payload.reason,
        step_id=task.step_id,
        meta={"task_id": task.id, **updates},
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/aprs/{apr_id}/approval/decision")
def approval_decision(
    apr_id: str,
    payload: schemas.ApprovalDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_approval_decision", _apr_workflow_identity(request, current_user, apr_id), limit=20, window_seconds=60)
    _ensure_permission(current_user, "approval.decide")
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    decision = payload.decision
    reason = (payload.reason or "").strip() or None
    if decision in {"reject", "request_evidence"} and not reason:
        raise ApiError(status_code=422, code="validation_error", message="Motivo obrigatorio", field="reason")

    selected_approver_id = payload.approved_by_user_id
    selected_approver_name = (payload.approved_by_name or "").strip() or None
    approver_user: User | None = None
    if selected_approver_id is not None:
        approver_user = db.get(User, selected_approver_id)
        if not approver_user or not approver_user.is_active:
            raise ApiError(status_code=422, code="validation_error", message="Aprovador invalido", field="approved_by_user_id")
        if approver_user.company_id != apr.company_id:
            raise ApiError(status_code=403, code="forbidden", message="Aprovador fora da empresa", field="approved_by_user_id")
        selected_approver_name = approver_user.name or approver_user.email

    task_id: int | None = None
    if decision == "approve":
        matrix_validation = _build_matrix_validation(apr, db)
        if not matrix_validation["ready"]:
            issues = matrix_validation.get("issues") or []
            first_issue = str(issues[0]) if issues else "Matriz de risco incompleta."
            raise ApiError(
                status_code=422,
                code="matrix_incomplete",
                message=first_issue,
                field="decision",
            )
        if not selected_approver_name:
            selected_approver_name = current_user.name or current_user.email
        if not selected_approver_name:
            raise ApiError(
                status_code=422,
                code="validation_error",
                message="Informe quem aprovou a APR",
                field="approved_by_name",
            )
        apr.status = "final"
        apr.current_stage = "relatorio"
        apr.approved_by_user_id = selected_approver_id or current_user.id
        apr.approved_by_name = selected_approver_name
        apr.approved_at = datetime.utcnow()
        event_name = "approval_approved"
    elif decision == "reject":
        apr.status = "reprovado"
        apr.current_stage = "controles"
        apr.approved_by_user_id = None
        apr.approved_by_name = None
        apr.approved_at = None
        event_name = "approval_rejected"
    else:
        apr.status = "reprovado"
        apr.current_stage = "controles"
        apr.approved_by_user_id = None
        apr.approved_by_name = None
        apr.approved_at = None
        event_name = "evidence_requested"
        task = APRTask(
            apr_id=apr.id,
            company_id=apr.company_id,
            step_id=None,
            type="evidence_request",
            title="Solicitacao de evidencia adicional",
            description=reason,
            assigned_to_user_id=apr.user_id,
            requested_by_user_id=current_user.id,
            priority="high",
            status="open",
            due_at=payload.due_at,
            reason=reason,
        )
        db.add(task)
        db.flush()
        task_id = task.id

    _append_audit_event(
        db,
        apr,
        event_name,
        actor=current_user,
        reason=reason,
        stage=apr.current_stage,
        meta={
            "decision": decision,
            "task_id": task_id,
            "due_at": payload.due_at.isoformat() if payload.due_at else None,
            "status": normalize_status(apr.status),
            "approved_by_user_id": apr.approved_by_user_id,
            "approved_by_name": apr.approved_by_name,
            "approved_at": apr.approved_at.isoformat() if apr.approved_at else None,
        },
    )
    db.commit()
    db.refresh(apr)

    return {
        "apr_id": apr.external_id or str(apr.id),
        "decision": decision,
        "status": normalize_status(apr.status),
        "current_stage": apr.current_stage,
        "task_id": task_id,
        "approved_by_user_id": apr.approved_by_user_id,
        "approved_by_name": apr.approved_by_name,
        "approved_at": apr.approved_at.isoformat() if apr.approved_at else None,
    }


@router.post("/aprs/{apr_id}/execution/{action}", response_model=schemas.ExecutionActionOut)
def execution_action(
    apr_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_execution_action", _apr_workflow_identity(request, current_user, f"{apr_id}:{action}"), limit=30, window_seconds=60)
    _ensure_permission(current_user, "evidence.upload")
    if action not in {"start", "pause", "finish"}:
        raise ApiError(status_code=404, code="not_found", message="Acao invalida", field="action")

    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    if action == "start":
        apr.current_stage = "execucao"
        event_name = "execution_started"
    elif action == "pause":
        apr.current_stage = "execucao"
        event_name = "execution_paused"
    else:
        apr.current_stage = "relatorio"
        if normalize_status(apr.status) == "submitted":
            apr.status = "aprovado"
        event_name = "execution_finished"

    _append_audit_event(
        db,
        apr,
        event_name,
        actor=current_user,
        stage=apr.current_stage,
        meta={"execution_action": action, "status": normalize_status(apr.status)},
    )
    db.commit()
    db.refresh(apr)
    now = datetime.utcnow()

    return {
        "apr_id": apr.id,
        "action": action,
        "status": normalize_status(apr.status),
        "current_stage": apr.current_stage,
        "timestamp": now,
    }


@router.get("/aprs/{apr_id}/audit", response_model=list[schemas.AuditEventOut])
def get_apr_audit(
    apr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_permission(current_user, "dashboard.view_limited")
    apr = _resolve_apr(apr_id, db)
    _ensure_same_company(apr, current_user)

    events = (
        db.execute(select(APREvent).where(APREvent.apr_id == apr.id).order_by(APREvent.criado_em.asc()))
        .scalars()
        .all()
    )

    out: list[dict[str, Any]] = []
    for event in events:
        payload = _parse_event_payload(event.payload)
        actor = payload.get("actor") if isinstance(payload.get("actor"), dict) else {}
        actor_user_id = payload.get("actor_user_id") or actor.get("id")
        actor_role = payload.get("actor_role") or actor.get("role")
        action = payload.get("action") or event.event
        reason = payload.get("reason")
        stage = _safe_stage(payload.get("stage"))
        step_id = payload.get("step_id")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        out.append(
            {
                "id": event.id,
                "timestamp": event.criado_em,
                "actor_user_id": actor_user_id,
                "actor_role": actor_role,
                "action": str(action),
                "reason": reason if isinstance(reason, str) else None,
                "apr_id": apr.id,
                "stage": stage,
                "step_id": int(step_id) if isinstance(step_id, int) else None,
                "meta": meta,
            }
        )
    return out


@router.get("/home/summary", response_model=schemas.HomeSummaryOut)
def get_home_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_permission(current_user, "dashboard.view_limited")
    company_id = current_user.company_id
    if not company_id:
        return {
            "kpis": {
                "aprs_open": 0,
                "critical": 0,
                "pending_approvals": 0,
                "sla_on_track": 0,
                "compliance_30d": 100,
            },
            "queue": [],
            "dashboards": {},
            "evidences": [],
        }

    aprs = db.execute(select(APR).where(APR.company_id == company_id)).scalars().all()
    apr_ids = [item.id for item in aprs]
    open_aprs = [item for item in aprs if normalize_status(item.status) != "archived"]
    pending_approvals = sum(1 for item in aprs if normalize_status(item.status) == "submitted")

    high_risk_apr_ids = set(
        db.execute(
            select(RiskItem.apr_id).where(RiskItem.apr_id.in_(apr_ids), RiskItem.score >= 13).distinct()
        ).scalars()
    ) if apr_ids else set()

    missing_evidence_apr_ids = set(
        db.execute(
            select(Passo.apr_id)
            .where(Passo.apr_id.in_(apr_ids), Passo.evidence_filename.is_(None))
            .distinct()
        ).scalars()
    ) if apr_ids else set()

    critical = len(high_risk_apr_ids.intersection(missing_evidence_apr_ids))

    now = datetime.utcnow()
    overdue_tasks = db.execute(
        select(func.count())
        .select_from(APRTask)
        .where(
            APRTask.company_id == company_id,
            APRTask.status.in_(tuple(_TASK_OPEN_STATUSES)),
            APRTask.due_at.is_not(None),
            APRTask.due_at < now,
        )
    ).scalar_one()
    sla_on_track = max(len(open_aprs) - overdue_tasks, 0)

    last_30d = now - timedelta(days=30)
    recent_steps = db.execute(
        select(Passo).where(Passo.company_id == company_id, Passo.atualizado_em >= last_30d)
    ).scalars().all()
    if recent_steps:
        with_evidence = sum(1 for step in recent_steps if step.evidence_filename)
        compliance_30d = round((with_evidence / len(recent_steps)) * 100)
    else:
        compliance_30d = 100

    task_rows = db.execute(
        select(APRTask)
        .where(APRTask.company_id == company_id, APRTask.status.in_(tuple(_TASK_OPEN_STATUSES)))
        .order_by(APRTask.due_at.is_(None), APRTask.due_at.asc(), APRTask.created_at.desc())
        .limit(20)
    ).scalars().all()

    apr_lookup = {item.id: item for item in aprs}
    queue = [
        {
            "task_id": task.id,
            "apr_id": apr_lookup.get(task.apr_id).external_id if apr_lookup.get(task.apr_id) else str(task.apr_id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "stage": apr_lookup.get(task.apr_id).current_stage if apr_lookup.get(task.apr_id) else None,
        }
        for task in task_rows
    ]

    risk_by_area_counter = Counter((item.sector or item.worksite or "Sem area") for item in open_aprs)
    risk_by_area = [
        {"area": area, "count": count}
        for area, count in risk_by_area_counter.most_common(6)
    ]

    pending_by_approver_counter = Counter()
    for task in task_rows:
        if task.assigned_to_user_id:
            pending_by_approver_counter[str(task.assigned_to_user_id)] += 1
    pending_by_approver = [
        {"approver": user_id, "count": count}
        for user_id, count in pending_by_approver_counter.most_common(6)
    ]

    risk_descriptions = [
        item.risk_description.strip()
        for item in db.execute(select(RiskItem).where(RiskItem.apr_id.in_(apr_ids))).scalars().all()
        if (item.risk_description or "").strip()
    ] if apr_ids else []
    top_hazards = [
        {"hazard": label, "count": count}
        for label, count in Counter(risk_descriptions).most_common(5)
    ]

    evidence_rows = db.execute(
        select(Passo)
        .where(Passo.company_id == company_id)
        .order_by(Passo.atualizado_em.desc())
        .limit(30)
    ).scalars().all()
    evidences = [
        {
            "step_id": step.id,
            "apr_id": apr_lookup.get(step.apr_id).external_id if apr_lookup.get(step.apr_id) else str(step.apr_id),
            "status": "completo" if step.evidence_filename else "faltando",
            "updated_at": step.atualizado_em.isoformat() if step.atualizado_em else None,
            "uploaded_at": step.evidence_uploaded_at.isoformat() if step.evidence_uploaded_at else None,
            "stage": apr_lookup.get(step.apr_id).current_stage if apr_lookup.get(step.apr_id) else None,
        }
        for step in evidence_rows
    ]

    return {
        "kpis": {
            "aprs_open": len(open_aprs),
            "critical": critical,
            "pending_approvals": pending_approvals,
            "sla_on_track": sla_on_track,
            "compliance_30d": compliance_30d,
        },
        "queue": queue,
        "dashboards": {
            "risk_by_area": risk_by_area,
            "top_hazards": top_hazards,
            "pending_by_approver": pending_by_approver,
        },
        "evidences": evidences,
    }
