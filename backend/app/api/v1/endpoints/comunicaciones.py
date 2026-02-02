"""
Endpoints de comunicaciones (WhatsApp y Email).
Listado desde conversacion_cobranza (WhatsApp) y configuración; respuesta desde configuracion?tab=whatsapp.
Las comunicaciones de clientes se reciben por WhatsApp (webhook) o email; se puede responder por ambos.
"""
import re
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.deps import get_current_user
from pydantic import BaseModel
from sqlalchemy import or_

from app.core.database import get_db
from sqlalchemy.orm import Session

from app.models.conversacion_cobranza import ConversacionCobranza
from app.models.cliente import Cliente

router = APIRouter(dependencies=[Depends(get_current_user)])


def _digits(s: str) -> str:
    return re.sub(r"\D", "", (s or "").strip()


def _cliente_id_por_telefono(db: Session, telefono: str) -> Optional[int]:
    """Devuelve cliente_id si existe un cliente cuyo teléfono (solo dígitos) coincide."""
    dig = _digits(telefono)
    if not dig or len(dig) < 8:
        return None
    for c in db.query(Cliente).all():
        cd = _digits(c.telefono or "")
        if cd == dig or (len(dig) >= 10 and dig.endswith(cd[-10:])) or (len(cd) >= 10 and cd.endswith(dig[-10:])):
            return c.id
    return None


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
    Listado de comunicaciones. WhatsApp: desde conversacion_cobranza (mensajes recibidos por webhook).
    Email: stub vacío hasta integración IMAP. Filtros: tipo, cliente_id, direccion; paginación page/per_page.
    """
    comunicaciones: list = []
    total = 0

    # Solo WhatsApp por ahora; si tipo == 'email' devolver vacío
    if tipo and tipo.lower() == "email":
        return {
            "comunicaciones": [],
            "paginacion": {"page": page, "per_page": per_page, "total": 0, "pages": 0},
        }

    q = db.query(ConversacionCobranza).order_by(ConversacionCobranza.updated_at.desc())
    if cliente_id is not None:
        cliente_row = db.get(Cliente, cliente_id)
        if not cliente_row or not cliente_row.telefono:
            return {"comunicaciones": [], "paginacion": {"page": page, "per_page": per_page, "total": 0, "pages": 0}}
        dig_cliente = _digits(cliente_row.telefono)
        suf = dig_cliente[-10:] if len(dig_cliente) >= 10 else dig_cliente
        q = q.filter(
            or_(
                ConversacionCobranza.telefono == dig_cliente,
                ConversacionCobranza.telefono.like(f"%{suf}"),
            )
        )
    total = q.count()
    offset = (page - 1) * per_page
    rows = q.offset(offset).limit(per_page).all()

    for row in rows:
        telefono_display = row.telefono if (row.telefono or "").startswith("+") else f"+{row.telefono}"
        cid = _cliente_id_por_telefono(db, row.telefono)
        nombre = (row.nombre_cliente or "").strip() or telefono_display
        comunicaciones.append({
            "id": row.id,
            "tipo": "whatsapp",
            "from_contact": telefono_display,
            "to_contact": "",
            "subject": None,
            "body": row.estado or "Mensaje recibido",
            "timestamp": row.updated_at.isoformat() if row.updated_at else "",
            "direccion": "INBOUND",
            "cliente_id": cid,
            "ticket_id": None,
            "requiere_respuesta": False,
            "procesado": True,
            "respuesta_enviada": True,
            "creado_en": row.updated_at.isoformat() if row.updated_at else "",
            "nombre_contacto": nombre,
        })

    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "comunicaciones": comunicaciones,
        "paginacion": {"page": page, "per_page": per_page, "total": total, "pages": pages},
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


class EnviarWhatsAppRequest(BaseModel):
    to_number: str
    message: str


@router.post("/enviar-whatsapp", response_model=dict)
def enviar_whatsapp(payload: EnviarWhatsAppRequest, db: Session = Depends(get_db)):
    """
    Envía un mensaje de WhatsApp desde Comunicaciones (modo manual).
    Usa la configuración de Configuración > WhatsApp. Respeta modo_pruebas (redirige al teléfono de pruebas si está activo).
    """
    from app.core.whatsapp_send import send_whatsapp_text
    from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db
    to_number = (payload.to_number or "").strip()
    message = (payload.message or "").strip()
    if not to_number or len(to_number) < 10:
        raise HTTPException(status_code=400, detail="Indica un número de destino válido (código de país + número).")
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    whatsapp_sync_from_db()
    cfg = get_whatsapp_config()
    modo_pruebas = (cfg.get("modo_pruebas") or "true").lower() == "true"
    telefono_pruebas = (cfg.get("telefono_pruebas") or "").strip()
    destino = telefono_pruebas if modo_pruebas and telefono_pruebas else to_number
    ok, error_meta = send_whatsapp_text(destino, message)
    if ok:
        return {"success": True, "mensaje": "Mensaje enviado.", "telefono_destino": destino}
    return {"success": False, "mensaje": error_meta or "No se pudo enviar.", "telefono_destino": destino}


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
