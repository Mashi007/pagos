"""
CRM CampaÃ±as: envÃ­o de correo masivo por lotes a todos los correos registrados en tabla clientes.
Evita congestiÃ³n y polÃ­ticas Gmail enviando en lotes con delay configurable.
"""
import logging
import time
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.crm_campana import CampanaCrm
from app.models.crm_campana_envio import CampanaEnvioCrm
from app.schemas.crm_campana import (
    CampanaCrmCreate,
    CampanaCrmUpdate,
    CampanaCrmResponse,
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
    Devuelve lista (cliente_id, email, nombres) de clientes con email vÃ¡lido.
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


@router.get("/preview-destinatarios", response_model=dict)
def preview_destinatarios(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Vista previa: total de correos Ãºnicos en clientes y una muestra.
    Ãštil antes de crear una campaÃ±a.
    """
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
    """Listado paginado de campaÃ±as CRM."""
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
    Crea una campaÃ±a en estado borrador.
    total_destinatarios se calcula con los correos Ãºnicos de la tabla clientes.
    """
    total = len(_get_destinatarios_clientes(db))
    row = CampanaCrm(
        nombre=payload.nombre,
        asunto=payload.asunto,
        cuerpo_texto=payload.cuerpo_texto,
        cuerpo_html=payload.cuerpo_html,
        estado="borrador",
        total_destinatarios=total,
        enviados=0,
        fallidos=0,
        batch_size=payload.batch_size,
        delay_entre_batches_seg=payload.delay_entre_batches_seg,
        usuario_creacion=current_user.email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CampanaCrmResponse.model_validate(row)


@router.get("/{campana_id}", response_model=CampanaCrmResponse)
def get_campana(campana_id: int, db: Session = Depends(get_db)):
    """Detalle de una campaÃ±a."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="CampaÃ±a no encontrada")
    return CampanaCrmResponse.model_validate(row)


@router.patch("/{campana_id}", response_model=CampanaCrmResponse)
def actualizar_campana(
    campana_id: int,
    payload: CampanaCrmUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza campaÃ±a solo si estÃ¡ en borrador."""
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="CampaÃ±a no encontrada")
    if row.estado != "borrador":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede editar una campaÃ±a en estado borrador",
        )
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return CampanaCrmResponse.model_validate(row)


def _run_envio_lotes(campana_id: int) -> None:
    """
    Tarea en segundo plano: envÃ­a por lotes a todos los correos de clientes.
    Usa SessionLocal propia para no depender de la sesiÃ³n del request.
    """
    db = SessionLocal()
    try:
        campana = db.get(CampanaCrm, campana_id)
        if not campana or campana.estado not in ("borrador", "enviando"):
            logger.warning("CampaÃ±a %s no existe o no estÃ¡ en borrador/enviando", campana_id)
            return
        if campana.estado == "borrador":
            campana.estado = "enviando"
            campana.fecha_envio_inicio = datetime.utcnow()
            db.commit()

        destinatarios = _get_destinatarios_clientes(db)
        from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio

        batch_size = max(5, min(100, campana.batch_size))
        delay = max(1, min(60, campana.delay_entre_batches_seg))
        enviados = campana.enviados
        fallidos = campana.fallidos

        for i in range(0, len(destinatarios), batch_size):
            lote = destinatarios[i : i + batch_size]
            if not get_email_activo_servicio("campanas"):
                continue
            for cliente_id, email, _ in lote:
                ok, err = send_email(
                    [email],
                    campana.asunto,
                    campana.cuerpo_texto,
                    body_html=campana.cuerpo_html or None,
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
            campana.estado = "completada"
            campana.fecha_envio_fin = datetime.utcnow()
            campana.enviados = enviados
            campana.fallidos = fallidos
            db.commit()
        logger.info("CampaÃ±a %s completada: enviados=%s fallidos=%s", campana_id, enviados, fallidos)
    except Exception as e:
        logger.exception("Error en envÃ­o campaÃ±a %s: %s", campana_id, e)
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


@router.post("/{campana_id}/iniciar-envio", response_model=dict)
def iniciar_envio(
    campana_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Inicia el envÃ­o por lotes en segundo plano.
    Responde de inmediato; el envÃ­o continÃºa en background.
    Solo permitido si la campaÃ±a estÃ¡ en borrador.
    """
    row = db.get(CampanaCrm, campana_id)
    if not row:
        raise HTTPException(status_code=404, detail="CampaÃ±a no encontrada")
    if row.estado != "borrador":
        raise HTTPException(
            status_code=400,
            detail="Solo se puede iniciar una campaÃ±a en estado borrador",
        )
    if row.total_destinatarios == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay destinatarios (ningÃºn correo vÃ¡lido en tabla clientes)",
        )
    background_tasks.add_task(_run_envio_lotes, campana_id)
    return {
        "success": True,
        "mensaje": "EnvÃ­o iniciado en segundo plano. Los correos se enviarÃ¡n por lotes.",
        "total_destinatarios": row.total_destinatarios,
        "batch_size": row.batch_size,
        "delay_entre_batches_seg": row.delay_entre_batches_seg,
    }


@router.get("/{campana_id}/envios", response_model=dict)
def listar_envios_campana(
    campana_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de envÃ­os (destinatarios) de una campaÃ±a."""
    campana = db.get(CampanaCrm, campana_id)
    if not campana:
        raise HTTPException(status_code=404, detail="CampaÃ±a no encontrada")
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
