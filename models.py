from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from database import Base

class EPI(Base):
    __tablename__ = "epis"
    id = Column(Integer, primary_key=True)
    epi = Column(String(255), nullable=False)            # vem da coluna "epi"
    descricao = Column(Text, nullable=True)              # vem da coluna "descricao"
    normas = Column(Text, nullable=True)                 # vem da coluna "normas"

    __table_args__ = (UniqueConstraint("epi", name="uq_epis_epi"),)


class Perigo(Base):
    __tablename__ = "perigos"
    id = Column(Integer, primary_key=True)
    perigo = Column(String(255), nullable=False)         # vem da coluna "perigo"
    consequencias = Column(Text, nullable=True)          # vem da coluna "consequencias"
    salvaguardas = Column(Text, nullable=True)           # vem da coluna "salvaguardas"

    __table_args__ = (UniqueConstraint("perigo", name="uq_perigos_perigo"),)
