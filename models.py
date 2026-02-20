from datetime import datetime
import json
from uuid import uuid4
from sqlalchemy import Column, Integer, String, Text, UniqueConstraint, ForeignKey, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from database import Base
from plan_utils import DEFAULT_PLAN, normalize_plan_name

class EPI(Base):
    __tablename__ = "epis"

    id = Column(Integer, primary_key=True)
    epi = Column(String, nullable=False)
    descricao = Column(Text)
    normas = Column(Text)

    __table_args__ = (UniqueConstraint("epi", name="uq_epi"),)


class Perigo(Base):
    __tablename__ = "perigos"

    id = Column(Integer, primary_key=True)
    perigo = Column(String, nullable=False)
    consequencias = Column(Text)
    salvaguardas = Column(Text)
    default_severity = Column(Integer, nullable=False, default=0)
    default_probability = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("perigo", name="uq_perigo"),)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    cnpj = Column(String(32), nullable=True, unique=True, index=True)
    plan_name = Column(String(20), nullable=False, default=DEFAULT_PLAN, server_default=DEFAULT_PLAN)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="company", lazy="selectin")
    aprs = relationship("APR", back_populates="company", lazy="selectin")
    invites = relationship("Invite", back_populates="company", lazy="selectin")

    @property
    def plan(self) -> str:
        return normalize_plan_name(self.plan_name)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="tecnico")

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    api_token = Column(String(64), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="users")
    aprs = relationship("APR", back_populates="user", lazy="selectin")
    invites_sent = relationship(
        "Invite",
        back_populates="inviter",
        foreign_keys="Invite.invited_by",
        lazy="selectin",
    )
    invites_accepted = relationship(
        "Invite",
        back_populates="acceptor",
        foreign_keys="Invite.accepted_by",
        lazy="selectin",
    )


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))

    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)
    hazards_json = Column("hazards", Text, nullable=False, default="[]")
    controls_json = Column("controls", Text, nullable=False, default="[]")
    worksite = Column(String(255), nullable=True)
    sector = Column(String(255), nullable=True)
    responsible = Column(String(255), nullable=True)
    activity_id = Column(String(64), nullable=True, index=True)
    activity_name = Column(String(255), nullable=True)
    date = Column(Date, nullable=True)
    source_hashes = Column(Text, nullable=True)
    template_version = Column(String(20), nullable=True)
    dangerous_energies_checklist_json = Column("dangerous_energies_checklist", Text, nullable=True)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(30), nullable=False, default="rascunho")

    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    passos = relationship(
        "Passo",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Passo.ordem",
    )
    risk_items = relationship(
        "RiskItem",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RiskItem.id",
    )
    company = relationship("Company", back_populates="aprs")
    user = relationship("User", back_populates="aprs")
    events = relationship(
        "APREvent",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="APREvent.criado_em",
    )
    shares = relationship(
        "APRShare",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="APRShare.criado_em",
    )

    @property
    def dangerous_energies_checklist(self) -> dict:
        defaults = {
            "hydraulic": False,
            "residual": False,
            "kinetic": False,
            "mechanical": False,
            "electrical": False,
            "gravitational_potential": False,
            "thermal": False,
            "pneumatic": False,
        }
        raw = self.dangerous_energies_checklist_json
        if not raw:
            return dict(defaults)
        try:
            data = json.loads(raw)
        except Exception:
            return dict(defaults)
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        if not isinstance(data, dict):
            return dict(defaults)
        normalized = dict(defaults)
        for key in defaults:
            normalized[key] = bool(data.get(key, False))
        return normalized

    @dangerous_energies_checklist.setter
    def dangerous_energies_checklist(self, value) -> None:
        defaults = {
            "hydraulic": False,
            "residual": False,
            "kinetic": False,
            "mechanical": False,
            "electrical": False,
            "gravitational_potential": False,
            "thermal": False,
            "pneumatic": False,
        }
        data = value
        if hasattr(value, "model_dump"):
            data = value.model_dump()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = None
        if not isinstance(data, dict):
            data = {}
        normalized = dict(defaults)
        for key in defaults:
            normalized[key] = bool(data.get(key, False))
        self.dangerous_energies_checklist_json = json.dumps(normalized, ensure_ascii=False)

    @property
    def hazards(self) -> list[dict]:
        raw = self.hazards_json
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    @hazards.setter
    def hazards(self, value) -> None:
        if not isinstance(value, list):
            self.hazards_json = "[]"
            return
        normalized = [item for item in value if isinstance(item, dict)]
        self.hazards_json = json.dumps(normalized, ensure_ascii=False)

    @property
    def controls(self) -> list[dict]:
        raw = self.controls_json
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    @controls.setter
    def controls(self, value) -> None:
        if not isinstance(value, list):
            self.controls_json = "[]"
            return
        normalized = [item for item in value if isinstance(item, dict)]
        self.controls_json = json.dumps(normalized, ensure_ascii=False)


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, index=True)

    apr_id = Column(Integer, ForeignKey("aprs.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)

    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)

    perigos = Column(Text, nullable=False, default="")
    riscos = Column(Text, nullable=False, default="")
    medidas_controle = Column(Text, nullable=False, default="")
    epis = Column(Text, nullable=False, default="")
    normas = Column(Text, nullable=False, default="")

    evidence_type = Column(String(20), nullable=True)
    evidence_filename = Column(String(255), nullable=True)
    evidence_caption = Column(Text, nullable=True)
    evidence_uploaded_at = Column(DateTime, nullable=True)

    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    apr = relationship("APR", back_populates="passos")
    risk_items = relationship(
        "RiskItem",
        back_populates="passo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (UniqueConstraint("apr_id", "ordem", name="uq_passo_apr_ordem"),)

    @property
    def technical_evidence(self):
        if not self.evidence_filename:
            return None
        return {
            "type": self.evidence_type or "image",
            "url": f"/v1/aprs/{self.apr_id}/passos/{self.id}/evidencia",
            "caption": self.evidence_caption,
            "uploaded_at": self.evidence_uploaded_at,
        }


class RiskItem(Base):
    __tablename__ = "risk_items"

    id = Column(Integer, primary_key=True)
    apr_id = Column(Integer, ForeignKey("aprs.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    step_id = Column(Integer, ForeignKey("passos.id", ondelete="CASCADE"), nullable=False, index=True)
    hazard_id = Column(Integer, ForeignKey("perigos.id", ondelete="SET NULL"), nullable=True, index=True)

    risk_description = Column(Text, nullable=False)
    probability = Column(Integer, nullable=False, default=0)
    severity = Column(Integer, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="invalid")

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    apr = relationship("APR", back_populates="risk_items")
    passo = relationship("Passo", back_populates="risk_items")
    hazard = relationship("Perigo")


class APREvent(Base):
    __tablename__ = "apr_events"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, ForeignKey("aprs.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    event = Column(String(50), nullable=False)
    payload = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    apr = relationship("APR", back_populates="events")


class APRShare(Base):
    __tablename__ = "apr_shares"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, ForeignKey("aprs.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    apr = relationship("APR", back_populates="shares")


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="tecnico")
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    accepted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="invites")
    inviter = relationship("User", foreign_keys=[invited_by], back_populates="invites_sent")
    acceptor = relationship("User", foreign_keys=[accepted_by], back_populates="invites_accepted")
