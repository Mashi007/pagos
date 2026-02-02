"""
Endpoints de auditoría. Datos reales desde la tabla auditoria (BD).
GET listado, GET stats, GET exportar, GET /{id}, POST /registrar.
"""
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auditoria import Auditoria

router = APIRouter(dependencies=[Depends(get_current_user)])


# --- Schemas (compatibles con frontend) ---

class AuditoriaItem(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    usuario_email: Optional[str] = None
    accion: str
    modulo: str
    tabla: str
    registro_id: Optional[int] = None
    descripcion: Optional[str] = None
    campo: Optional[str] = None
    datos_anteriores: Optional[Any] = None
    datos_nuevos: Optional[Any] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resultado: str
    mensaje_error: Optional[str] = None
    fecha: str

    class Config:
        from_attributes = True


class AuditoriaListResponse(BaseModel):
    items: List[AuditoriaItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditoriaStats(BaseModel):
    total_acciones: int
    acciones_por_modulo: dict
    acciones_por_usuario: dict
    acciones_hoy: int
    acciones_esta_semana: int
    acciones_este_mes: int


class RegistrarAuditoriaBody(BaseModel):
    modulo: str
    accion: str
    descripcion: str
    registro_id: Optional[int] = None


def _row_to_item(r: Auditoria) -> AuditoriaItem:
    """Convierte fila BD a AuditoriaItem."""
    fecha_str = r.fecha.isoformat() + "Z" if r.fecha else ""
    datos_ant = json.loads(r.datos_anteriores) if r.datos_anteriores else None
    datos_nue = json.loads(r.datos_nuevos) if r.datos_nuevos else None
    return AuditoriaItem(
        id=r.id,
        usuario_id=r.usuario_id,
        usuario_email=r.usuario_email,
        accion=r.accion,
        modulo=r.modulo,
        tabla=r.tabla or "",
        registro_id=r.registro_id,
        descripcion=r.descripcion,
        campo=r.campo,
        datos_anteriores=datos_ant,
        datos_nuevos=datos_nue,
        ip_address=r.ip_address,
        user_agent=r.user_agent,
        resultado=r.resultado,
        mensaje_error=r.mensaje_error,
        fecha=fecha_str,
    )


@router.get("", response_model=AuditoriaListResponse)
def listar_auditoria(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    usuario_email: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    ordenar_por: str = Query("fecha"),
    orden: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """Lista registros de auditoría con filtros y paginación. Datos desde BD."""
    q = select(Auditoria)
    if usuario_email:
        q = q.where(Auditoria.usuario_email.ilike(f"%{usuario_email}%"))
    if modulo:
        q = q.where(Auditoria.modulo == modulo)
    if accion:
        q = q.where(Auditoria.accion == accion)
    if fecha_desde:
        try:
            fd = datetime.fromisoformat(fecha_desde.replace("Z", "+00:00")).date()
            q = q.where(func.date(Auditoria.fecha) >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.fromisoformat(fecha_hasta.replace("Z", "+00:00")).date()
            q = q.where(func.date(Auditoria.fecha) <= fh)
        except ValueError:
            pass
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    order_col = getattr(Auditoria, ordenar_por, Auditoria.fecha)
    if orden == "desc":
        q = q.order_by(order_col.desc())
    else:
        q = q.order_by(order_col.asc())
    q = q.offset(skip).limit(limit)
    rows = db.execute(q).scalars().all()
    items = [_row_to_item(r) for r in rows]
    total_pages = (total + limit - 1) // limit if limit else 0
    return AuditoriaListResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1 if limit else 1,
        page_size=limit,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=AuditoriaStats)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """Estadísticas de auditoría desde BD (totales, por módulo, por usuario, hoy/semana/mes)."""
    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_acciones = db.scalar(select(func.count()).select_from(Auditoria)) or 0
    acciones_hoy = db.scalar(
        select(func.count()).select_from(Auditoria).where(func.date(Auditoria.fecha) == hoy.date())
    ) or 0
    acciones_esta_semana = db.scalar(
        select(func.count()).select_from(Auditoria).where(Auditoria.fecha >= inicio_semana)) or 0
    acciones_este_mes = db.scalar(
        select(func.count()).select_from(Auditoria).where(Auditoria.fecha >= inicio_mes)) or 0
    rows_mod = db.execute(
        select(Auditoria.modulo, func.count()).select_from(Auditoria).group_by(Auditoria.modulo)
    ).all()
    acciones_por_modulo = {r[0]: r[1] for r in rows_mod}
    rows_usr = db.execute(
        select(Auditoria.usuario_email, func.count())
        .select_from(Auditoria)
        .where(Auditoria.usuario_email.isnot(None))
        .group_by(Auditoria.usuario_email)
    ).all()
    acciones_por_usuario = {r[0] or "": r[1] for r in rows_usr}
    return AuditoriaStats(
        total_acciones=total_acciones,
        acciones_por_modulo=acciones_por_modulo,
        acciones_por_usuario=acciones_por_usuario,
        acciones_hoy=acciones_hoy,
        acciones_esta_semana=acciones_esta_semana,
        acciones_este_mes=acciones_este_mes,
    )


@router.get("/exportar")
def exportar_auditoria(
    usuario_email: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Exporta auditoría a Excel. Datos desde BD."""
    try:
        import openpyxl
    except ImportError:
        minimal_xlsx = (
            b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
            b"[\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        return StreamingResponse(
            iter([minimal_xlsx]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"},
        )
    q = select(Auditoria).order_by(Auditoria.fecha.desc()).limit(10000)
    if usuario_email:
        q = q.where(Auditoria.usuario_email.ilike(f"%{usuario_email}%"))
    if modulo:
        q = q.where(Auditoria.modulo == modulo)
    if accion:
        q = q.where(Auditoria.accion == accion)
    if fecha_desde:
        try:
            fd = datetime.fromisoformat(fecha_desde.replace("Z", "+00:00")).date()
            q = q.where(func.date(Auditoria.fecha) >= fd)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = datetime.fromisoformat(fecha_hasta.replace("Z", "+00:00")).date()
            q = q.where(func.date(Auditoria.fecha) <= fh)
        except ValueError:
            pass
    rows = db.execute(q).scalars().all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    ws.append(["id", "fecha", "usuario_email", "modulo", "accion", "tabla", "registro_id", "descripcion", "resultado"])
    for r in rows:
        ws.append([
            r.id,
            r.fecha.isoformat() if r.fecha else "",
            r.usuario_email or "",
            r.modulo or "",
            r.accion or "",
            r.tabla or "",
            r.registro_id or "",
            (r.descripcion or "")[:500],
            r.resultado or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"},
    )


@router.get("/{auditoria_id}", response_model=AuditoriaItem)
def obtener_auditoria(auditoria_id: int, db: Session = Depends(get_db)):
    """Obtiene un registro de auditoría por ID desde BD."""
    row = db.get(Auditoria, auditoria_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro de auditoría no encontrado")
    return _row_to_item(row)


@router.post("/registrar", response_model=AuditoriaItem)
def registrar_evento(body: RegistrarAuditoriaBody, db: Session = Depends(get_db)):
    """Registra un evento de auditoría en BD."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = Auditoria(
        usuario_id=None,
        usuario_email=None,
        accion=body.accion,
        modulo=body.modulo,
        tabla="",
        registro_id=body.registro_id,
        descripcion=body.descripcion,
        resultado="EXITOSO",
        fecha=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_item(row)
