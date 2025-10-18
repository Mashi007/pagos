from pydantic import BaseModel, ConfigDict
from typing import List

class ConcesionarioBase(BaseModel):
    pass

class ConcesionarioCreate(ConcesionarioBase):
    pass

class ConcesionarioUpdate(BaseModel):
    pass

class ConcesionarioResponse(ConcesionarioBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class ConcesionarioListResponse(BaseModel):
    items: List[ConcesionarioResponse]
    total: int
    page: int
    size: int
    pages: int
