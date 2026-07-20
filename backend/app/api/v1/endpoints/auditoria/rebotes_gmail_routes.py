"""
Submodulo Auditoria: rebotes Gmail (notificaciones@) en bandeja Principal de itmaster.
"""
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services import auditoria_rebotes_gmail_service as svc

router = APIRouter(prefix="/rebotes-gmail", tags=["auditoria-rebotes-gmail"])


class ReboteGmailItem(BaseModel):
    id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    cedula: Optional[str] = None
    correo: str
    observaciones: str
    asunto_gmail: Optional[str] = None
    remitente_detectado: Optional[str] = None
    etiqueta_gmail: Optional[str] = None
    fecha_mensaje: Optional[str] = None
    fecha_registro: Optional[str] = None
    procesado_por: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReboteGmailListResponse(BaseModel):
    items: List[ReboteGmailItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProcesarRebotesResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    mensaje: Optional[str] = None
    query: Optional[str] = None
    etiqueta: Optional[str] = None
    revisados: int = 0
    guardados: int = 0
    omitidos: int = 0
    ya_existentes: int = 0
    etiquetados: int = 0
    sin_correo: int = 0


class BorrarRebotesResponse(BaseModel):
    borrados: int


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _to_item(row) -> ReboteGmailItem:
    return ReboteGmailItem(
        id=row.id,
        gmail_message_id=row.gmail_message_id,
        gmail_thread_id=row.gmail_thread_id,
        cedula=row.cedula,
        correo=row.correo,
        observaciones=row.observaciones,
        asunto_gmail=row.asunto_gmail,
        remitente_detectado=row.remitente_detectado,
        etiqueta_gmail=row.etiqueta_gmail,
        fecha_mensaje=_iso(row.fecha_mensaje),
        fecha_registro=_iso(row.fecha_registro),
        procesado_por=row.procesado_por,
    )


@router.post("/procesar", response_model=ProcesarRebotesResponse)
def procesar_rebotes_gmail(
    max_messages: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    """Escaneo manual: Primary de itmaster (leidos y no leidos), cuerpo con notificaciones@, etiqueta GMAIL, guarda en BD."""
    result = svc.procesar_rebotes_gmail(
        db,
        procesado_por=admin.email,
        max_messages=max_messages,
    )
    if not result.get("ok") and result.get("error") == "no_credentials":
        raise HTTPException(status_code=503, detail=result.get("mensaje") or "Sin credenciales Gmail")
    if not result.get("ok") and result.get("error") == "gmail_list_failed":
        raise HTTPException(status_code=502, detail=result.get("mensaje") or "Error listando Gmail")
    return ProcesarRebotesResponse(**result)


@router.get("", response_model=ReboteGmailListResponse)
def listar_rebotes_gmail(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
):
    rows, total = svc.listar_rebotes(db, skip=skip, limit=limit)
    page_size = limit
    page = (skip // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return ReboteGmailListResponse(
        items=[_to_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/excel")
def exportar_rebotes_gmail_excel(
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
):
    """Excel desde BD: cedula, correo, observaciones (+ trazas)."""
    import openpyxl

    rows, _total = svc.listar_rebotes(db, skip=0, limit=100000)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rebotes Gmail"
    ws.append(
        [
            "cedula",
            "correo",
            "observaciones",
            "asunto_gmail",
            "fecha_mensaje",
            "fecha_registro",
            "procesado_por",
            "gmail_message_id",
        ]
    )
    for r in rows:
        ws.append(
            [
                r.cedula or "",
                r.correo,
                r.observaciones,
                r.asunto_gmail or "",
                _iso(r.fecha_mensaje) or "",
                _iso(r.fecha_registro) or "",
                r.procesado_por or "",
                r.gmail_message_id,
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="auditoria_rebotes_gmail_{stamp}.xlsx"'
        },
    )


@router.delete("", response_model=BorrarRebotesResponse)
def borrar_todos_rebotes_gmail(
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
):
    """Borra todos los registros guardados en auditoria_rebotes_gmail."""
    n = svc.borrar_todos(db)
    return BorrarRebotesResponse(borrados=n)
