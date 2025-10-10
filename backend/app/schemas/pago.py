from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PagoBase(BaseModel):
    """Schema base para Pago"""
    monto: Decimal = Field(gt=0, decimal_places=2, description="Monto del pago")
    fecha_pago: datetime = Field(description="Fecha del pago")
    metodo_pago: str = Field(default="EFECTIVO", max_length=20)
    referencia: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None


class PagoCreate(PagoBase):
    """Schema para crear un pago"""
    prestamo_id: int = Field(gt=0, description="ID del préstamo")


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""
    monto: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    fecha_pago: Optional[datetime] = None
    metodo_pago: Optional[str] = Field(None, max_length=20)
    referencia: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None
    estado: Optional[str] = Field(None, max_length=20)
    
    model_config = ConfigDict(from_attributes=True)


class PagoResponse(BaseModel):
    """Schema para respuesta de un pago"""
    id: int
    prestamo_id: int
    monto: Decimal
    fecha_pago: datetime
    metodo_pago: str
    referencia: Optional[str]
    estado: str
    monto_capital: Decimal
    monto_interes: Decimal
    saldo_restante: Decimal
    creado_en: datetime
    actualizado_en: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class PagoList(BaseModel):
    """Schema para lista paginada de pagos"""
    items: List[PagoResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def create(cls, items: List[PagoResponse], total: int, page: int = 1, page_size: int = 50):
        """Helper para crear instancia con cálculo automático de páginas"""
        import math
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
