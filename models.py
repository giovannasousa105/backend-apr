from sqlalchemy import Column, Integer, Text, String, ForeignKey
from database import Base


class Atividade(Base):
    __tablename__ = "atividades"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
    local = Column(Text, nullable=False)
    funcao = Column(Text, nullable=False)


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    atividade_id = Column(Integer, ForeignKey("atividades.id"), nullable=False)
    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)
    perigos = Column(Text, nullable=False)
    riscos = Column(Text, nullable=False)
    medidas_controle = Column(Text, nullable=False)
    epis = Column(Text, nullable=False)
    normas = Column(Text, nullable=False)


class Epi(Base):
    __tablename__ = "epis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
    descricao = Column(Text, nullable=False)
    normas = Column(Text, nullable=False)


class Perigo(Base):
    __tablename__ = "perigos"

    id = Column(Integer, primary_key=True, index=True)
    perigo = Column(Text, nullable=False)
    consequencias = Column(Text, nullable=False)
    salvaguardas = Column(Text, nullable=False)


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    risco = Column(String(50), nullable=False)
