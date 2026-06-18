from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date as dt_date
from typing import Optional, List, Generic, TypeVar, Literal, Any

from text_normalizer import normalize_text


class NormalizedModel(BaseModel):
    __origin__ = "unknown"

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value, info):
        field_name = getattr(info, "field_name", None)
        return _normalize_value(value, origin=cls.__origin__, field=field_name)


class NormalizedUserModel(NormalizedModel):
    __origin__ = "user"


class DangerousEnergiesChecklist(NormalizedModel):
    model_config = ConfigDict(extra="forbid")

    hydraulic: bool = False
    residual: bool = False
    kinetic: bool = False
    mechanical: bool = False
    electrical: bool = False
    gravitational_potential: bool = False
    thermal: bool = False
    pneumatic: bool = False


AprStage = Literal["criar", "perigos", "controles", "aprovacao", "execucao", "relatorio"]
RiskLevel = Literal["baixa", "media", "alta"]
TaskStatus = Literal["open", "in_progress", "done", "canceled"]


def _normalize_value(value, *, origin: str, field: str | None):
    if isinstance(value, str):
        return normalize_text(value, origin=origin, field=field)
    if isinstance(value, list):
        normalized = []
        for idx, item in enumerate(value):
            child_field = f"{field}[{idx}]" if field else None
            normalized.append(_normalize_value(item, origin=origin, field=child_field))
        return normalized
    if isinstance(value, dict):
        normalized = {}
        for key, val in value.items():
            child_field = f"{field}.{key}" if field else str(key)
            normalized[key] = _normalize_value(val, origin=origin, field=child_field)
        return normalized
    return value


# ---------- EPI / PERIGO ----------
class EPIOut(NormalizedModel):
    id: int
    epi: str
    descricao: Optional[str] = None
    normas: Optional[str] = None

    class Config:
        from_attributes = True


class PerigoOut(NormalizedModel):
    id: int
    perigo: str
    consequencias: Optional[str] = None
    salvaguardas: Optional[str] = None
    default_severity: int = 0
    default_probability: int = 0

    class Config:
        from_attributes = True


class PerigoUpdate(NormalizedUserModel):
    default_severity: Optional[int] = None
    default_probability: Optional[int] = None


# ---------- Paginação (genérico) ----------
T = TypeVar("T")

class PaginatedOut(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int


class PaginatedEPIOut(PaginatedOut[EPIOut]):
    pass

class PaginatedPerigoOut(PaginatedOut[PerigoOut]):
    pass


# ---------- APR / PASSO ----------
class PassoCreate(NormalizedUserModel):
    ordem: int = Field(..., ge=1)
    descricao: str

    perigos: str = ""
    riscos: str = ""
    medidas_controle: str = ""
    epis: str = ""
    normas: str = ""


class PassoUpdate(NormalizedUserModel):
    ordem: Optional[int] = Field(None, ge=1)
    descricao: Optional[str] = None

    perigos: Optional[str] = None
    riscos: Optional[str] = None
    medidas_controle: Optional[str] = None
    epis: Optional[str] = None
    normas: Optional[str] = None


class TechnicalEvidenceOut(NormalizedModel):
    type: Optional[str] = None
    url: Optional[str] = None
    caption: Optional[str] = None
    uploaded_at: Optional[datetime] = None


class PassoOut(NormalizedModel):
    id: int
    apr_id: int
    ordem: int
    descricao: str

    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str

    technical_evidence: Optional[TechnicalEvidenceOut] = None

    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class RiskItemOut(NormalizedModel):
    id: int
    apr_id: int
    step_id: int
    hazard_id: Optional[int] = None
    risk_description: str
    probability: int
    severity: int
    score: int
    risk_level: str
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskItemUpdate(NormalizedUserModel):
    probability: Optional[int] = None
    severity: Optional[int] = None


class PassoBulkItem(NormalizedUserModel):
    step_order: int = Field(..., ge=1)
    description: str
    hazards: List[str] = []
    risks: List[str] = []
    measures: List[str] = []
    epis: List[str] = []
    regulations: List[str] = []


class PassoBulkCreate(NormalizedUserModel):
    items: List[PassoBulkItem]
    replace: bool = False


class APRCreate(NormalizedUserModel):
    worksite: Optional[str] = None
    sector: Optional[str] = None
    responsible: Optional[str] = None
    contract_id: Optional[str] = None
    unit_id: Optional[str] = None
    date: Optional[dt_date] = None
    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    titulo: Optional[str] = None
    risco: Optional[str] = None
    descricao: Optional[str] = None
    dangerous_energies_checklist: Optional[DangerousEnergiesChecklist] = None


class APRUpdate(NormalizedUserModel):
    worksite: Optional[str] = None
    sector: Optional[str] = None
    responsible: Optional[str] = None
    contract_id: Optional[str] = None
    unit_id: Optional[str] = None
    date: Optional[dt_date] = None
    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    titulo: Optional[str] = None
    risco: Optional[str] = None
    descricao: Optional[str] = None
    dangerous_energies_checklist: Optional[DangerousEnergiesChecklist] = None


class APRFinalize(NormalizedUserModel):
    responsible_confirm: str
    position: Optional[str] = None
    crea: Optional[str] = None


class APROut(NormalizedModel):
    id: int
    titulo: str
    risco: str
    descricao: Optional[str] = None
    worksite: Optional[str] = None
    sector: Optional[str] = None
    responsible: Optional[str] = None
    contract_id: Optional[str] = None
    unit_id: Optional[str] = None
    date: Optional[dt_date] = None
    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    source_hashes: Optional[str] = None
    template_version: Optional[str] = None
    norm_profile_id: Optional[int] = None
    norm_profile_version: Optional[int] = None
    norm_profile_mode: Optional[str] = None
    norm_profile_snapshot: Optional[dict[str, Any]] = None
    company_id: Optional[int] = None
    user_id: Optional[int] = None
    status: str
    current_stage: AprStage = "criar"
    approved_by_user_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    dangerous_energies_checklist: DangerousEnergiesChecklist = Field(
        default_factory=DangerousEnergiesChecklist
    )

    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class APRDetail(APROut):
    passos: List[PassoOut] = []
    risk_items: List[RiskItemOut] = []


class ActivityOut(NormalizedModel):
    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    regulation: Optional[str] = None
    tags: List[str] = []


class ActivitySuggestionSummary(NormalizedModel):
    hazards: List[str] = []
    risks: List[str] = []
    measures: List[str] = []
    epis: List[str] = []
    regulations: List[str] = []


class ActivitySuggestionStep(NormalizedModel):
    step_order: int
    description: str
    hazards: List[str] = []
    risks: List[str] = []
    measures: List[str] = []
    epis: List[str] = []
    regulations: List[str] = []


class ActivitySuggestions(NormalizedModel):
    activity: ActivityOut
    suggestions: ActivitySuggestionSummary
    steps: List[ActivitySuggestionStep] = []


class ActivityApply(NormalizedUserModel):
    activity_id: Optional[str] = None
    replace: bool = True


class APREventOut(NormalizedModel):
    id: int
    apr_id: int
    event: str
    payload: Optional[dict] = None
    criado_em: datetime


class APRStageUpdate(NormalizedUserModel):
    stage: AprStage
    reason: Optional[str] = None


class APRTaskCreate(NormalizedUserModel):
    step_id: Optional[int] = None
    type: str = "generic"
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    priority: str = "normal"
    due_at: Optional[datetime] = None
    reason: Optional[str] = None


class APRTaskUpdate(NormalizedUserModel):
    status: Optional[TaskStatus] = None
    assigned_to_user_id: Optional[int] = None
    priority: Optional[str] = None
    due_at: Optional[datetime] = None
    reason: Optional[str] = None


class APRTaskOut(NormalizedModel):
    id: int
    apr_id: int
    company_id: Optional[int] = None
    step_id: Optional[int] = None
    type: str
    title: str
    description: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    requested_by_user_id: Optional[int] = None
    priority: str
    status: TaskStatus
    due_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedAPRTaskOut(PaginatedOut[APRTaskOut]):
    pass


class ApprovalDecisionRequest(NormalizedUserModel):
    decision: Literal["approve", "reject", "request_evidence"]
    reason: Optional[str] = None
    due_at: Optional[datetime] = None
    approved_by_user_id: Optional[int] = None
    approved_by_name: Optional[str] = None


class ExecutionActionOut(NormalizedModel):
    apr_id: int
    action: Literal["start", "pause", "finish"]
    status: str
    current_stage: AprStage
    timestamp: datetime


class AuditEventPayload(NormalizedModel):
    actor: Optional[dict[str, Any]] = None
    action: str
    reason: Optional[str] = None
    stage: Optional[AprStage] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class AuditEventOut(NormalizedModel):
    id: int
    timestamp: datetime
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: str
    reason: Optional[str] = None
    apr_id: int
    stage: Optional[AprStage] = None
    step_id: Optional[int] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class HomeSummaryKPI(NormalizedModel):
    aprs_open: int
    critical: int
    pending_approvals: int
    sla_on_track: int
    compliance_30d: int


class HomeSummaryOut(NormalizedModel):
    kpis: HomeSummaryKPI
    queue: List[dict[str, Any]] = []
    dashboards: dict[str, Any] = Field(default_factory=dict)
    evidences: List[dict[str, Any]] = []


class APRShareOut(NormalizedModel):
    apr_id: int
    token: str
    share_url: str
    filename: str
    created_at: datetime


class PlanLimit(NormalizedModel):
    max_active_aprs: int | None
    ai_generations_per_month: int | None
    evidence_per_step: int | None


class PlanFeature(NormalizedModel):
    pdf_logo: bool
    pdf_watermark: bool
    template_library: bool
    checklist_nr: bool
    history: bool
    duplicate_apr: bool
    ai_assistant: bool


class PlanUsage(NormalizedModel):
    active_aprs: int
    active_aprs_limit: int | None


class PlanSummary(NormalizedModel):
    name: str
    limits: PlanLimit
    features: PlanFeature
    usage: PlanUsage


class AccountMetrics(NormalizedModel):
    company_id: int
    company_name: Optional[str] = None
    company_plan: str
    users_total: int
    users_active: int
    aprs_total: int
    aprs_active: int
    aprs_created_30d: int


class SellerActivationChecklistItem(NormalizedUserModel):
    __origin__ = "seller_activation"

    label: str
    completed: bool


class SellerActivationStatusPayload(NormalizedUserModel):
    __origin__ = "seller_activation"

    seller_id: Optional[str] = None
    checklist: List[SellerActivationChecklistItem] = Field(..., min_length=1)


class SellerActivationStatusOut(NormalizedModel):
    __origin__ = "seller_activation"

    seller_id: Optional[str] = None
    status: str
    total_items: int
    completed_items: int
    progress_percent: int
    pending_items: List[str]
    checklist: List[SellerActivationChecklistItem]
    message: str


class NormFrameworkOut(NormalizedModel):
    id: str
    type: str
    name: str
    description: Optional[str] = None
    country_scope: Optional[str] = None
    is_base: bool = False
    is_enabled_global: bool = True


class NormProfileBaseOut(NormalizedModel):
    id: str
    type: str
    name: Optional[str] = None


class NormProfileResolvedOut(NormalizedModel):
    profileId: str
    id: int
    version: int
    scopeType: str
    scopeId: str
    base: NormProfileBaseOut
    optionals: List[NormProfileBaseOut] = []
    riskEngineMode: str
    updatedAt: Optional[str] = None
    updatedBy: Optional[int] = None
    resolvedFrom: Optional[str] = None


class NormProfileUpsert(NormalizedUserModel):
    scope_type: Literal["company", "contract", "unit"]
    scope_id: str
    optional_framework_ids: List[str] = []
    risk_engine_mode: Optional[str] = None


class NormProfileUpdate(NormalizedUserModel):
    optional_framework_ids: Optional[List[str]] = None
    risk_engine_mode: Optional[str] = None


class RiskCalcStepInput(NormalizedUserModel):
    step_order: int = Field(..., ge=1)
    probability: int = Field(..., ge=1, le=5)
    severity: int = Field(..., ge=1, le=5)


class RiskCalcInput(NormalizedUserModel):
    aprId: Optional[int] = None
    normProfileId: Optional[int] = None
    profileVersion: Optional[int] = None
    contractId: Optional[str] = None
    unitId: Optional[str] = None
    steps: List[RiskCalcStepInput] = []


class RiskCalcStepOut(NormalizedModel):
    stepOrder: int
    probability: int
    severity: int
    score: int
    riskLevel: str


class RiskCalcTotalsOut(NormalizedModel):
    totalSteps: int
    baixo: int
    medio: int
    alto: int
    maxScore: int


class RiskCalcOut(NormalizedModel):
    aprId: Optional[int] = None
    normProfileId: int
    profileVersionUsed: int
    riskEngineMode: str
    engineVersion: str
    steps: List[RiskCalcStepOut] = []
    totals: RiskCalcTotalsOut
