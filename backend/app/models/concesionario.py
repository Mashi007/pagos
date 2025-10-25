from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


from datetime import date
class Concesionario(Base):

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    updated_at = Column
    )


    def __repr__(self):
        return 
            f"activo={self.activo})>"
        )


    def to_dict(self):
        return 
        }
