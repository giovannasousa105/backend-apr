from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from database import Base


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

    __table_args__ = (UniqueConstraint("perigo", name="uq_perigo"),)
