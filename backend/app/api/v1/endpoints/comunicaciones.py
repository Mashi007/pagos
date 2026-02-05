"""
Endpoints de comunicaciones (WhatsApp y Email).
Listado desde conversacion_cobranza (WhatsApp) y configuración; respuesta desde configuracion?tab=whatsapp.
Las comunicaciones de clientes se reciben por WhatsApp (webhook) o email; se puede responder por ambos.
"""
import re
import time
from typing import Optional, Dict, List, Tuple, Any

from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.deps import get_current_user
from app.schemas.auth import UserResponse
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models.conversacion_cobranza import ConversacionCobranza
from app.models.cliente import Cliente
from app.models.mensaje_whatsapp import MensajeWhatsapp

router = APIRouter(dependencies=[Depends(get_current_user)])


def _digits(s: str) -> str:
    return re.sub(r"\D", "", (s or "").strip())


def _build_telefono_to_cliente_index(db: Session) -> Tuple[Dict[str, int], Dict[str, List[Tuple[str, int]]]]:
    """
    Una sola query a clientes: construye índices por dígitos completos y por sufijo (10 dígitos)
    para búsqueda O(1) / O(k) por conversación en lugar de O(N×M).
    """
    by_full: Dict[str, int] = {}
    by_suffix: Dict[str, List[Tuple[str, int]]] = {}
    for c in db.query(Cliente).all():
        cd = _digits(c.telefono or "")
        if not cd or len(cd) < 8:
            continue
        by_full[cd] = c.id
        if len(cd) >= 10:
            suf = cd[-10:]
            by_suffix.setdefault(suf, []).append((cd, c.id))
    return by_full, by_suffix


def _lookup_cliente_id(phone_digits: str, by_full: Dict[str, int], by_suffix: Dict[str, List[Tuple[str, int]]]) -> Optional[int]:
    """Busca cliente_id por teléfono normalizado (coincidencia exacta o por sufijo 10 dígitos)."""
    if not phone_digits or len(phone_digits) < 8:
        return None
    cid = by_full.get(phone_digits)
    if cid is not None:
        return cid
    if len(phone_digits) >= 10:
        for cd, id_ in by_suffix.get(phone_digits[-10:], []):
            if cd == phone_digits or (len(cd) >= 10 and phone_digits.endswith(cd[-10:])) or (len(phone_digits) >= 10 and cd.endswith(phone_digits[-10:])):
                return id_
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

    # Una sola carga de clientes + índice por teléfono (evita N+1)
    by_full, by_suffix = _build_telefono_to_cliente_index(db)
    cids_en_pagina = set()
    for row in rows:
        cid = _lookup_cliente_id(_digits(row.telefono), by_full, by_suffix)
        if cid is not None:
            cids_en_pagina.add(cid)
    clientes_pagina: Dict[int, Cliente] = {}
    if cids_en_pagina:
        for c in db.query(Cliente).filter(Cliente.id.in_(cids_en_pagina)).all():
            clientes_pagina[c.id] = c

    for row in rows:
        telefono_display = row.telefono if (row.telefono or "").startswith("+") else f"+{row.telefono}"
        cid = _lookup_cliente_id(_digits(row.telefono), by_full, by_suffix)
        nombre = (row.nombre_cliente or "").strip()
        if not nombre and cid and cid in clientes_pagina:
            nombre = (clientes_pagina[cid].nombres or "").strip()
        nombre = nombre or telefono_display
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
            "cedula": (row.cedula or "").strip() or None,
            "estado_cobranza": row.estado or None,
        })

    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "comunicaciones": comunicaciones,
        "paginacion": {"page": page, "per_page": per_page, "total": total, "pages": pages},
    }


@router.get("/mensajes", response_model=dict)
def listar_mensajes_whatsapp(
    telefono: str = Query(..., description="Teléfono de la conversación (ej. +593983000700)"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Historial de mensajes WhatsApp de una conversación (copia de lo hablado con el cliente).
    Devuelve mensajes ordenados por fecha para mostrar en Comunicaciones.
    """
    phone = _digits(telefono)
    if len(phone) < 8:
        return {"mensajes": []}
    rows = (
        db.query(MensajeWhatsapp)
        .where(MensajeWhatsapp.telefono == phone)
        .order_by(MensajeWhatsapp.timestamp.asc())
        .limit(limit)
        .all()
    )
    mensajes = [
        {
            "id": r.id,
            "body": r.body or "",
            "direccion": r.direccion,
            "message_type": r.message_type or "text",
            "timestamp": r.timestamp.isoformat() if r.timestamp else "",
        }
        for r in rows
    ]
    return {"mensajes": mensajes}


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


# Rate limit envío WhatsApp: máximo por usuario por ventana (evitar abuso)
_RATE_LIMIT_WHATSAPP: Dict[str, Tuple[int, float]] = {}
RATE_LIMIT_WHATSAPP_WINDOW_SEC = 60
RATE_LIMIT_WHATSAPP_MAX = 10


def _check_rate_limit_whatsapp(user: UserResponse) -> None:
    """Lanza HTTPException 429 si el usuario supera el límite de envíos por ventana."""
    key = (user.email or "unknown").strip()
    now = time.monotonic()
    if key not in _RATE_LIMIT_WHATSAPP or (now - _RATE_LIMIT_WHATSAPP[key][1]) > RATE_LIMIT_WHATSAPP_WINDOW_SEC:
        _RATE_LIMIT_WHATSAPP[key] = (0, now)
    count, start = _RATE_LIMIT_WHATSAPP[key]
    if count >= RATE_LIMIT_WHATSAPP_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Máximo {RATE_LIMIT_WHATSAPP_MAX} envíos por minuto. Espera un momento antes de volver a enviar.",
        )
    _RATE_LIMIT_WHATSAPP[key] = (count + 1, start)


class EnviarWhatsAppRequest(BaseModel):
    to_number: str
    message: str


@router.post("/enviar-whatsapp", response_model=dict)
def enviar_whatsapp(
    payload: EnviarWhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Envía un mensaje de WhatsApp desde Comunicaciones (modo manual).
    Usa la configuración de Configuración > WhatsApp. Respeta modo_pruebas.
    Rate limit: máximo 10 envíos por minuto por usuario.
    """
    _check_rate_limit_whatsapp(current_user)
    from app.core.whatsapp_send import send_whatsapp_text
    from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db
    from app.services.whatsapp_service import guardar_mensaje_whatsapp
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
        guardar_mensaje_whatsapp(db, destino, "OUTBOUND", message, "text")
        return {"success": True, "mensaje": "Mensaje enviado.", "telefono_destino": destino}
    return {"success": False, "mensaje": error_meta or "No se pudo enviar.", "telefono_destino": destino}


class CrearClienteAutomaticoRequest(BaseModel):
    telefono: Optional[str] = None
    email: Optional[str] = None
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None


def _normalize_for_duplicate(s: str) -> str:
    return (s or "").strip()


def _validar_cedula_formato_strict(cedula: str) -> bool:
    """Acepta formato E/J/V + 6-11 dígitos (cedula ya normalizada)."""
    t = (cedula or "").strip().upper()
    if len(t) < 7 or t[0] not in ("E", "J", "V"):
        return False
    return len(t) <= 12 and t[1:].isdigit() and 6 <= len(t) - 1 <= 11


def _validar_email_basico(email: str) -> bool:
    if not email or "@" not in email:
        return False
    local, _, domain = email.strip().partition("@")
    return bool(local and domain and "." in domain)


@router.post("/crear-cliente-automatico", response_model=dict)
def crear_cliente_automatico(payload: CrearClienteAutomaticoRequest, db: Session = Depends(get_db)):
    """
    Crear cliente desde una comunicación.
    Valida duplicados (cédula+nombres, email) y formatos; devuelve 409 si ya existe, 400 si datos inválidos.
    """
    from datetime import date

    cedula = _normalize_for_duplicate(payload.cedula)
    nombres = _normalize_for_duplicate(payload.nombres)
    email = _normalize_for_duplicate(payload.email)
    telefono = (payload.telefono or "").strip()
    telefono_dig = _digits(telefono)

    if not cedula:
        raise HTTPException(status_code=400, detail="La cédula es obligatoria.")
    if not nombres:
        raise HTTPException(status_code=400, detail="Los nombres son obligatorios.")
    if not _validar_cedula_formato_strict(cedula):
        raise HTTPException(status_code=400, detail="Cédula inválida. Use formato E, J o V seguido de 6 a 11 dígitos.")
    if email and not _validar_email_basico(email):
        raise HTTPException(status_code=400, detail="Formato de email inválido.")
    if telefono and len(telefono_dig) < 8:
        raise HTTPException(status_code=400, detail="Teléfono inválido (mínimo 8 dígitos).")

    # Duplicado por cédula + nombres (mismo criterio que clientes.py)
    existing_cn = db.execute(
        select(Cliente.id).where(
            Cliente.cedula == cedula,
            Cliente.nombres == nombres,
        )
    ).first()
    if existing_cn:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un cliente con la misma cédula y nombre. Cliente existente ID: {existing_cn[0]}",
        )
    if email:
        existing_email = db.execute(select(Cliente.id).where(Cliente.email == email)).first()
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con el mismo email. Cliente existente ID: {existing_email[0]}",
            )

    email_final = email or "actualizar@ejemplo.com"
    telefono_final = telefono if telefono_dig else "+580000000000"
    direccion = _normalize_for_duplicate(payload.direccion) or "Actualizar dirección"
    notas = _normalize_for_duplicate(payload.notas) or "Creado desde Comunicaciones"

    try:
        row = Cliente(
            cedula=cedula,
            nombres=nombres,
            telefono=telefono_final,
            email=email_final,
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
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "unique" in msg.lower() or "duplicate" in msg.lower() or "cedula" in msg.lower() or "email" in msg.lower():
            raise HTTPException(status_code=409, detail="Ya existe un cliente con esos datos (cédula o email).") from e
        raise HTTPException(status_code=400, detail="Error de integridad en los datos. Revise cédula y email.") from e
