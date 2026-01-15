from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    risco = Column(String(50), nullable=False)

    passos = relationship("Passo", back_populates="apr", cascade="all, delete")


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, ForeignKey("aprs.id"), nullable=False)

    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)
    perigos = Column(Text, nullable=False)
    riscos = Column(Text, nullable=False)
    medidas_controle = Column(Text, nullable=False)
    epis = Column(Text, nullable=False)
    normas = Column(Text, nullable=False)

    apr = relationship("APR", back_populates="passos")
