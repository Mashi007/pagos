from sqlalchemy import Column, Integer
from app.db.session import Base

class Concesionario(Base):
    __tablename__ = "concesionarios"

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<Concesionario(id={self.id})>"

    def to_dict(self):
        return {
            "id": self.id
        }
