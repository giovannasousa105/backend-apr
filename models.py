from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)

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


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, ForeignKey("aprs.id", ondelete="CASCADE"), nullable=False, index=True)

    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)

    perigos = Column(Text, nullable=False, default="")
    riscos = Column(Text, nullable=False, default="")
    medidas_controle = Column(Text, nullable=False, default="")
    epis = Column(Text, nullable=False, default="")
    normas = Column(Text, nullable=False, default="")

    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    apr = relationship("APR", back_populates="passos")
