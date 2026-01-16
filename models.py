from sqlalchemy import Column, Integer, String, Text
from database import Base


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text)

    def __repr__(self):
        return f"<APR id={self.id} titulo={self.titulo}>"
