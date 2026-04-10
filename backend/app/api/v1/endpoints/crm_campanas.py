"""
CRM Campañas: envío de correo masivo por lotes a todos los correos registrados en tabla clientes.
Evita congestión y políticas Gmail enviando en lotes con delay configurable.
"""
import base64
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from sqlalchemy import select, func, distinct
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.crm_campana import CampanaCrm
from app.models.crm_campana_destinatario import CampanaDestinatarioCrm
from app.models.crm_campana_envio import CampanaEnvioCrm
from app.schemas.crm_campana import (
    CampanaCrmCreate,
    CampanaCrmUpdate,
    CampanaCrmResponse,
    CampanaProgramarBody,
    DestinatarioPreview,
    CampanaDestinatarioResponse,
)
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _valid_email(s: str) -> bool:
    s = (s or "").strip()
    return bool(s and "@" in s and "." in s.split("@")[-1])


def _get_destinatarios_clientes(db: Session) -> List[Tuple[int, str, Optional[str]]]:
    """
    Devuelve lista (cliente_id, email, nombres) de clientes con email válido.
    Un solo registro por email (primer cliente que tenga ese email).
    """
    rows = (
        db.execute(
            select(Cliente.id, Cliente.email, Cliente.nombres)
            .where(Cliente.email.isnot(None))
            .order_by(Cliente.id)
        )
        .all()
    )
    seen: set = set()
    out: List[Tuple[int, str, Optional[str]]] = []
    for cliente_id, email, nombres in rows:
        if not email or not _valid_email(email):
            continue
        e = email.strip().lower()
        if e in seen:
            continue
        seen.add(e)
        out.append((cliente_id, email.strip(), (nombres or "").strip() or None))
    return out


def _get_destinatarios_para_campana(
    db: Session, campana: CampanaCrm
) -> List[Tuple[int, str, Optional[str]]]:
    """
    Si la campaña tiene filas en crm_campana_destinatario: solo esos clientes (con email válido).
    Si no tiene: todos los de tabla clientes (comportamiento anterior).
    """
    rows_dest = db.execute(
        select(CampanaDestinatarioCrm.cliente_id).where(
            CampanaDestinatarioCrm.campana_id == campana.id
        )
    ).all()
    dest_ids = [r[0] for r in rows_dest]
    if not dest_ids:
        return _get_destinatarios_clientes(db)
    rows = (
        db.execute(
            select(Cliente.id, Cliente.email, Cliente.nombres)
            .where(Cliente.id.in_(dest_ids))
            .where(Cliente.email.isnot(None))
            .order_by(Cliente.id)
        )
        .all()
    )
    out: List[Tuple[int, str, Optional[str]]] = []
    seen: set = set()
    for cliente_id, email, nombres in rows:
        if not email or not _valid_email(email):
            continue
        e = email.strip().lower()
        if e in seen:
            continue
        seen.add(e)
        out.append((cliente_id, email.strip(), (nombres or "").strip() or None))
    return out


def _get_destinatarios_by_ids(
    db: Session, ids: List[int]
) -> List[Tuple[int, str, Optional[str]]]:
    """Devuelve (cliente_id, email, nombres) solo para los IDs indicados (con email válido)."""
    if not ids:
        return []
    ids_unicos = list(dict.fromkeys(ids))
    rows = (
        db.execute(
            select(Cliente.id, Cliente.email, Cliente.nombres)
            .where(Cliente.id.in_(ids_unicos))
            .where(Cliente.email.isnot(None))
            .order_by(Cliente.id)
        )
        .all()
    )
    out: List[Tuple[int, str, Optional[str]]] = []
    seen: set = set()
    for cliente_id, email, nombres in rows:
        if not email or not _valid_email(email):
            continue
        e = email.strip().lower()
        if e in seen:
            continue
        seen.add(e)
        out.append((cliente_id, email.strip(), (nombres or "").strip() or None))
    return out


@router.get("/preview-destinatarios", response_model=dict)
def preview_destinatarios(
    limit: int = Query(50, ge=1, le=500),
    ids: Optional[str] = Query(None, description="IDs de cliente separados por coma; si se envían, solo se devuelven esos contactos"),
    db: Session = Depends(get_db),
):
    """
    Vista previa: si `ids` viene informado, solo los contactos seleccionados (esos IDs).
    Si no, total de correos únicos en clientes y una muestra.
    """
    if ids and ids.strip():
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        destinatarios = _get_destinatarios_by_ids(db, id_list)
    else:
        destinatarios = _get_destinatarios_clientes(db)
    total = len(destinatarios)
    muestra = [
        DestinatarioPreview(email=e, cliente_id=cid, nombres=nombres)
        for cid, e, nombres in destinatarios[:limit]
    ]
    return {
        "total": total,
        "muestra": muestra,
    }


@router.get("", response_model=dict)
def listar_campanas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de campañas CRM."""
    q = select(CampanaCrm).order_by(CampanaCrm.fecha_creacion.desc())
    count_q = select(func.count()).select_from(CampanaCrm)
    if estado and estado.strip():
        q = q.where(CampanaCrm.estado == estado.strip())
        count_q = count_q.where(CampanaCrm.estado == estado.strip())
    total = db.scalar(count_q) or 0
    offset = (page - 1) * per_page
    rows = db.execute(q.offset(offset).limit(per_page)).scalars().all()
    items = [CampanaCrmResponse.model_validate(r) for r in rows]
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "items": items,
        "paginacion": {"page": page, "per_page": per_page, "total": total, "pages": pages},
    }


@router.post("", response_model=CampanaCrmResponse)
def crear_campana(
    payload: CampanaCrmCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Crea una campaña en estado borrador.
    Si destinatarios_cliente_ids viene con IDs: solo se envía a esos clientes.
    Si viene vacío o null: se envía a todos los correos de tabla clientes.
    """
    ids_a_guardar: List[int] = []
    if payload.destinatarios_cliente_ids and len(payload.destinatarios_cliente_ids) > 0:
        ids_unicos = list(dict.fromkeys(payload.destinatarios_cliente_ids))
        clientes_con_email = (
            db.execute(
                select(Cliente.id, Cliente.email)
                .where(Cliente.id.in_(ids_unicos))
                .where(Cliente.email.isnot(None))
            )
        ).all()
        validos = [(r[0], r[1]) for r in clientes_con_email if r[1] and _valid_email((r[1] or "").strip())]
        seen_emails: set = set()
        for cid, email in validos:
            e = (email or "").strip().lower()
            if e not in seen_emails:
                seen_emails.add(e)
                ids_a_guardar.append(cid)
        total = len(ids_a_guardar)
    else:
        total = len(_get_destinatarios_clientes(db))

    cc_str = ",".join(e.strip() for e in (payload.cc_emails or []) if e and isinstance(e, str) and "@" in (e.strip() or "")) or None
    adjunto_bytes = None
    adjunto_nombre = None
    if payload.adjunto_base64 and payload.adjunto_base64.strip():
        try:
            adjunto_bytes = base64.b64decode(payload.adjunto_base64)
            adjunto_nombre = (payload.adjunto_nombre or "adjunto").strip()[:255]
        except Exception:
            adjunto_bytes = None
            adjunto_nombre = None
    row = CampanaCrm(
        nombre=payload.nombre,
        asunto=payload.asunto,
        cuerpo_texto=payload.cuerpo_texto or "",
        cuerpo_html=payload.cuerpo_html,
        estado="borrador",
        total_destinatarios=total,
        enviados=0,
        fallidos=0,
        batch_size=payload.batch_size,
        delay_entre_batches_seg=payload.delay_entre_batches_seg,
        cc_emails=cc_str,
        adjunto_nombre=adjunto_nombre,
        adjunto_contenido=adjunto_bytes,
        usuario_creacion=current_user.email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if ids_a_guardar:
        for cid in ids_a_guardar:
            db.add(CampanaDestinatarioCrm(campana_id=row.id, cliente_id=cid))
        db.commit()
    return CampanaCrmResponse.model_validate(row)


@router.get("/{campana_id}", response_model=CampanaCrmResponse)
def get_campana(campana_id: int, db: Session = Depends(get_db)):
    """Detalle de una campaña."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return CampanaCrmResponse.model_validate(row)


@router.patch("/{campana_id}", response_model=CampanaCrmResponse)
def actualizar_campana(
    campana_id: int,
    payload: CampanaCrmUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza campaña solo si está en borrador."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if row.estado != "borrador":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede editar una campaña en estado borrador",
        )
    data = payload.model_dump(exclude_unset=True)
    cc_emails = data.pop("cc_emails", None)
    adjunto_nombre = data.pop("adjunto_nombre", None)
    adjunto_base64 = data.pop("adjunto_base64", None)
    for k, v in data.items():
        setattr(row, k, v)
    if cc_emails is not None:
        row.cc_emails = ",".join(e.strip() for e in cc_emails if e and isinstance(e, str) and "@" in (e.strip() or "")) or None
    if adjunto_base64 is not None and adjunto_base64.strip():
        try:
            row.adjunto_contenido = base64.b64decode(adjunto_base64)
            row.adjunto_nombre = (adjunto_nombre or "adjunto").strip()[:255] if adjunto_nombre else "adjunto"
        except Exception:
            pass
    elif adjunto_base64 is not None and not adjunto_base64.strip():
        row.adjunto_contenido = None
        row.adjunto_nombre = None
    db.commit()
    db.refresh(row)
    return CampanaCrmResponse.model_validate(row)


def _run_envio_lotes(campana_id: int) -> None:
    """
    Tarea en segundo plano: envía por lotes a todos los correos de clientes.
    Usa SessionLocal propia para no depender de la sesión del request.
    """
    db = SessionLocal()
    try:
        campana = db.get(CampanaCrm, campana_id)
        if not campana or campana.estado not in ("borrador", "enviando", "programada"):
            logger.warning("Campaña %s no existe o no está en borrador/enviando/programada", campana_id)
            return
        era_programada = bool(
            (getattr(campana, "programado_cada_dias", None) or 0) or (getattr(campana, "programado_cada_horas", None) or 0)
        )
        if campana.estado == "borrador" or campana.estado == "programada":
            campana.estado = "enviando"
            campana.fecha_envio_inicio = datetime.utcnow()
            db.commit()

        destinatarios = _get_destinatarios_para_campana(db, campana)
        from app.core.email import send_email
        from app.core.email_config_holder import get_email_activo_servicio
        from app.services.notificaciones_exclusion_desistimiento import (
            cliente_bloqueado_por_desistimiento,
        )

        cc_list: List[str] = []
        if campana.cc_emails and campana.cc_emails.strip():
            cc_list = [e.strip() for e in campana.cc_emails.split(",") if e and _valid_email(e.strip())]
        attachments: Optional[List[Tuple[str, bytes]]] = None
        if campana.adjunto_contenido and campana.adjunto_nombre:
            attachments = [(campana.adjunto_nombre, bytes(campana.adjunto_contenido))]

        batch_size = max(5, min(100, campana.batch_size))
        delay = max(1, min(60, campana.delay_entre_batches_seg))
        enviados = campana.enviados
        fallidos = campana.fallidos

        for i in range(0, len(destinatarios), batch_size):
            campana = db.get(CampanaCrm, campana_id)
            if campana and campana.estado == "cancelada":
                logger.info("Campaña %s detenida por el usuario (cancelada)", campana_id)
                break
            lote = destinatarios[i : i + batch_size]
            if not get_email_activo_servicio("campanas"):
                continue
            for cliente_id, email, _ in lote:
                if cliente_bloqueado_por_desistimiento(
                    db, cliente_id=cliente_id, email=email
                ):
                    logger.info(
                        "Campaña %s: omitir cliente_id=%s por DESISTIMIENTO",
                        campana_id,
                        cliente_id,
                    )
                    registro = CampanaEnvioCrm(
                        campana_id=campana_id,
                        cliente_id=cliente_id,
                        email=email,
                        estado="fallido",
                        fecha_envio=datetime.utcnow(),
                        error_mensaje="Bloqueado por regla DESISTIMIENTO",
                    )
                    db.add(registro)
                    fallidos += 1
                    db.commit()
                    continue
                ok, err = send_email(
                    [email],
                    campana.asunto,
                    campana.cuerpo_texto or "",
                    body_html=campana.cuerpo_html or None,
                    cc_emails=cc_list if cc_list else None,
                    attachments=attachments,
                    servicio="campanas",
                )
                registro = CampanaEnvioCrm(
                    campana_id=campana_id,
                    cliente_id=cliente_id,
                    email=email,
                    estado="enviado" if ok else "fallido",
                    fecha_envio=datetime.utcnow(),
                    error_mensaje=None if ok else (err or "Error desconocido"),
                )
                db.add(registro)
                if ok:
                    enviados += 1
                else:
                    fallidos += 1
                db.commit()

            campana = db.get(CampanaCrm, campana_id)
            if campana:
                campana.enviados = enviados
                campana.fallidos = fallidos
                db.commit()

            if i + batch_size < len(destinatarios):
                time.sleep(delay)

        campana = db.get(CampanaCrm, campana_id)
        if campana:
            now = datetime.utcnow()
            campana.fecha_envio_fin = now
            campana.enviados = enviados
            campana.fallidos = fallidos
            if era_programada and campana.estado != "cancelada":
                dias = getattr(campana, "programado_cada_dias", None) or 0
                horas = getattr(campana, "programado_cada_horas", None) or 0
                if dias or horas:
                    delta = timedelta(days=dias, hours=horas)
                    campana.programado_proxima_ejecucion = now + delta
                    campana.estado = "programada"
                    db.commit()
                    logger.info("Campaña %s programada: próxima ejecución %s", campana_id, campana.programado_proxima_ejecucion)
                    return
            campana.estado = "completada"
            db.commit()
        logger.info("Campaña %s completada: enviados=%s fallidos=%s", campana_id, enviados, fallidos)
    except Exception as e:
        logger.exception("Error en envío campaña %s: %s", campana_id, e)
        try:
            campana = db.get(CampanaCrm, campana_id)
            if campana:
                campana.estado = "completada"
                campana.fecha_envio_fin = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{campana_id}/parar", response_model=dict)
def parar_campana(campana_id: int, db: Session = Depends(get_db)):
    """Detiene un envío en curso. Solo permitido si la campaña está en estado enviando."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if row.estado != "enviando":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede parar una campaña que está enviando",
        )
    row.estado = "cancelada"
    row.fecha_envio_fin = datetime.utcnow()
    db.commit()
    return {"success": True, "mensaje": "Envío detenido. La campaña quedó en estado cancelada."}


@router.delete("/{campana_id}", status_code=204)
def eliminar_campana(campana_id: int, db: Session = Depends(get_db)):
    """Elimina una campaña. Solo permitido si está en borrador o cancelada."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if row.estado not in ("borrador", "cancelada"):
        raise HTTPException(
            status_code=400,
            detail="Solo se puede eliminar una campaña en borrador o cancelada",
        )
    db.delete(row)
    db.commit()
    return None


@router.post("/{campana_id}/programar", response_model=dict)
def programar_campana(
    campana_id: int,
    payload: CampanaProgramarBody,
):
    """
    Deshabilitado a propósito: no hay envíos CRM recurrentes por reloj en el producto.
    Los correos de campaña solo se disparan con POST /{id}/iniciar-envio (manual).
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "La programación automática por fecha u hora está deshabilitada. "
            "No existe proceso oculto que envíe campañas solas; use «iniciar envío» manualmente cuando corresponda."
        ),
    )


@router.post("/{campana_id}/iniciar-envio", response_model=dict)
def iniciar_envio(
    campana_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Inicia el envío por lotes en segundo plano.
    Responde de inmediato; el envío continúa en background.
    Solo permitido si la campaña está en borrador.
    """
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if row.estado != "borrador":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede iniciar una campaña en estado borrador",
        )
    if row.total_destinatarios == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay destinatarios (ningún correo válido en tabla clientes)",
        )
    background_tasks.add_task(_run_envio_lotes, campana_id)
    return {
        "success": True,
        "mensaje": "Envío iniciado en segundo plano. Los correos se enviarán por lotes.",
        "total_destinatarios": row.total_destinatarios,
        "batch_size": row.batch_size,
        "delay_entre_batches_seg": row.delay_entre_batches_seg,
    }


def ejecutar_campanas_programadas() -> None:
    """
    No utilizado: el producto no registra ningún job que llame a esta función.
    Las campañas no se envían por horario; POST /programar responde 501.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        try:
            rows = (
                db.execute(
                    select(CampanaCrm.id).where(
                        CampanaCrm.estado == "programada",
                        CampanaCrm.programado_proxima_ejecucion.isnot(None),
                        CampanaCrm.programado_proxima_ejecucion <= now,
                        CampanaCrm.total_destinatarios > 0,
                    )
                )
            ).all()
        except ProgrammingError as e:
            if "programado_proxima_ejecucion" in str(e):
                logger.warning(
                    "Columna programado_proxima_ejecucion no existe en crm_campana. "
                    "Ejecutar migración: alembic upgrade head (o backend/sql/crm_campanas_programar_columnas.sql)"
                )
                return
            raise
        for (campana_id,) in rows:
            try:
                _run_envio_lotes(campana_id)
            except Exception as e:
                logger.exception("Error ejecutando campaña programada %s: %s", campana_id, e)
    finally:
        db.close()


@router.get("/{campana_id}/envios", response_model=dict)
def listar_envios_campana(
    campana_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de envíos (destinatarios) de una campaña."""
    campana = db.get(CampanaCrm, campana_id)
    if not campana:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    q = (
        select(CampanaEnvioCrm)
        .where(CampanaEnvioCrm.campana_id == campana_id)
        .order_by(CampanaEnvioCrm.id)
    )
    if estado and estado.strip():
        q = q.where(CampanaEnvioCrm.estado == estado.strip())
    count_q = select(func.count()).select_from(CampanaEnvioCrm).where(
        CampanaEnvioCrm.campana_id == campana_id
    )
    if estado and estado.strip():
        count_q = count_q.where(CampanaEnvioCrm.estado == estado.strip())
    total = db.scalar(count_q) or 0
    offset = (page - 1) * per_page
    rows = db.execute(q.offset(offset).limit(per_page)).scalars().all()
    items = [CampanaDestinatarioResponse.model_validate(r) for r in rows]
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "items": items,
        "paginacion": {"page": page, "per_page": per_page, "total": total, "pages": pages},
    }
