"""
Endpoints de comunicaciones (WhatsApp y Email).
Listado y respuesta desde configuración (configuracion?tab=whatsapp y email).
Las comunicaciones de clientes se reciben por WhatsApp (webhook) o email; se puede responder por ambos.
"""
from typing import Optional
from fastapi import APIRouter, Query, Depends

from app.core.deps import get_current_user
from pydantic import BaseModel

from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_comunicaciones(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tipo: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    requiere_respuesta: Optional[bool] = Query(None),
    direccion: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Listado de comunicaciones (WhatsApp/Email). Configuración en configuracion?tab=whatsapp.
    Stub: devuelve lista vacía hasta tener tabla comunicaciones o integración con Meta/IMAP.
    Cuando exista fuente de datos: filtrar por tipo, cliente_id, requiere_respuesta, direccion;
    paginar con page/per_page; devolver formato ComunicacionUnificada (id, tipo, from_contact, body, timestamp, etc.).
    """
    return {
        "comunicaciones": [],
        "paginacion": {"page": page, "per_page": per_page, "total": 0, "pages": 0},
    }


@router.get("/por-responder", response_model=dict)
def obtener_comunicaciones_por_responder(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Comunicaciones que requieren respuesta. Stub hasta tener datos reales."""
    return {
        "comunicaciones": [],
        "paginacion": {"page": page, "per_page": per_page, "total": 0, "pages": 0},
    }


class CrearClienteAutomaticoRequest(BaseModel):
    telefono: Optional[str] = None
    email: Optional[str] = None
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None


@router.post("/crear-cliente-automatico", response_model=dict)
def crear_cliente_automatico(payload: CrearClienteAutomaticoRequest, db: Session = Depends(get_db)):
    """Crear cliente desde una comunicación. Stub: devuelve éxito con datos mínimos hasta tener lógica real."""
    from app.models.cliente import Cliente
    from datetime import date
    cedula = payload.cedula or "SIN-CEDULA"
    nombres = payload.nombres or "Cliente desde comunicación"
    telefono = payload.telefono or "+580000000000"
    email = payload.email or "noreply@ejemplo.com"
    direccion = payload.direccion or "Actualizar dirección"
    notas = payload.notas or "Creado desde Comunicaciones"
    row = Cliente(
        cedula=cedula,
        nombres=nombres,
        telefono=telefono,
        email=email,
        direccion=direccion,
        fecha_nacimiento=date(2000, 1, 1),
        ocupacion="Actualizar ocupación",
        estado="ACTIVO",
        usuario_registro="comunicaciones",
        notas=notas,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "success": True,
        "cliente": {"id": row.id, "cedula": row.cedula, "nombres": row.nombres, "telefono": row.telefono, "email": row.email},
    }
