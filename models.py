from sqlalchemy import Column, Integer, String, Text
from database import Base


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, nullable=False)  # sem ForeignKey por enquanto

    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)
    perigos = Column(Text, nullable=False)
    riscos = Column(Text, nullable=False)
    medidas_controle = Column(Text, nullable=False)
    epis = Column(Text, nullable=False)
    normas = Column(Text, nullable=False)
