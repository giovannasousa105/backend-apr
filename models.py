from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class APR(Base):
    __tablename__ = "aprs"

    # -------------------------
    # Identificação
    # -------------------------
    id = Column(Integer, primary_key=True, index=True)

    # -------------------------
    # Dados principais
    # -------------------------
    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)

    # -------------------------
    # Metadados (evolução futura)
    # -------------------------
    status = Column(
        String(30),
        nullable=False,
        default="rascunho",  # rascunho | validada | arquivada
    )

    criado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    atualizado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # -------------------------
    # Relacionamentos
    # -------------------------
    passos = relationship(
        "Passo",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Passo.ordem",
    )

    def __repr__(self) -> str:
        return f"<APR id={self.id} titulo='{self.titulo}' risco={self.risco}>"


class Passo(Base):
    __tablename__ = "passos"

    # -------------------------
    # Identificação
    # -------------------------
    id = Column(Integer, primary_key=True, index=True)

    apr_id = Column(
        Integer,
        ForeignKey("aprs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------
    # Conteúdo técnico
    # -------------------------
    ordem = Column(Integer, nullable=False)

    descricao = Column(Text, nullable=False)

    # Armazenados como texto (CSV ou JSON simples)
    perigos = Column(Text, nullable=False, default="")
    riscos = Column(Text, nullable=False, default="")
    medidas_controle = Column(Text, nullable=False, default="")
    epis = Column(Text, nullable=False, default="")
    normas = Column(Text, nullable=False, default="")

    # -------------------------
    # Metadados
    # -------------------------
    criado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    atualizado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # -------------------------
    # Relacionamento
    # -------------------------
    apr = relationship("APR", back_populates="passos")

    def __repr__(self) -> str:
        return f"<Passo id={self.id} apr_id={self.apr_id} ordem={self.ordem}>"
