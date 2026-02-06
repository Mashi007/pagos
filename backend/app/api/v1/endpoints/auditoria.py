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
    """Convierte fila BD a AuditoriaItem (entidad->modulo, entidad_id->registro_id, detalles->descripcion, exito->resultado)."""
    fecha_str = r.fecha.isoformat() + "Z" if r.fecha else ""
    return AuditoriaItem(
        id=r.id,
        usuario_id=r.usuario_id,
        usuario_email=None,
        accion=r.accion,
        modulo=r.entidad or "",
        tabla=r.entidad or "",
        registro_id=r.entidad_id,
        descripcion=r.detalles,
        campo=None,
        datos_anteriores=None,
        datos_nuevos=None,
        ip_address=r.ip_address,
        user_agent=r.user_agent,
        resultado="EXITOSO" if r.exito else "ERROR",
        mensaje_error=r.mensaje_error,
        fecha=fecha_str,
    )


@router.get("", response_model=AuditoriaListResponse)
def listar_auditoria(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    usuario_email: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    registro_id: Optional[int] = Query(None),
    accion: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    ordenar_por: str = Query("fecha"),
    orden: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """Lista registros de auditoría con filtros y paginación. Datos desde BD."""
    q = select(Auditoria)
    if modulo:
        q = q.where(Auditoria.entidad == modulo)
    if registro_id is not None:
        q = q.where(Auditoria.entidad_id == registro_id)
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
    col_name = {"modulo": "entidad", "registro_id": "entidad_id"}.get(ordenar_por, ordenar_por)
    order_col = getattr(Auditoria, col_name, Auditoria.fecha)
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
        select(Auditoria.entidad, func.count()).select_from(Auditoria).group_by(Auditoria.entidad)
    ).all()
    acciones_por_modulo = {r[0] or "": r[1] for r in rows_mod}
    rows_usr = db.execute(
        select(Auditoria.usuario_id, func.count()).select_from(Auditoria).group_by(Auditoria.usuario_id)
    ).all()
    acciones_por_usuario = {str(r[0]) if r[0] is not None else "": r[1] for r in rows_usr}
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
    if modulo:
        q = q.where(Auditoria.entidad == modulo)
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
    ws.append(["id", "fecha", "usuario_id", "entidad", "accion", "entidad_id", "detalles", "exito"])
    for r in rows:
        ws.append([
            r.id,
            r.fecha.isoformat() if r.fecha else "",
            r.usuario_id or "",
            r.entidad or "",
            r.accion or "",
            r.entidad_id or "",
            (r.detalles or "")[:500],
            "SI" if r.exito else "NO",
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
def registrar_evento(
    body: RegistrarAuditoriaBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Registra un evento de auditoría en BD. usuario_id se toma del usuario autenticado."""
    now = datetime.now(timezone.utc)
    row = Auditoria(
        usuario_id=current_user.id,
        accion=body.accion,
        entidad=body.modulo,
        entidad_id=body.registro_id,
        detalles=body.descripcion,
        exito=True,
        fecha=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_item(row)
