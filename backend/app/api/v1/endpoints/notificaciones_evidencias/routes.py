"""
API Evidencias (Notificaciones): escanear Gmail itmaster, buscar y descargar PDF.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services import evidencias_notificacion_service as svc

router = APIRouter(tags=["notificaciones-evidencias"])


class EvidenciaItem(BaseModel):
    id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    etiqueta_gmail: str
    email_cliente: str
    cedula: Optional[str] = None
    asunto: Optional[str] = None
    fecha_mensaje: Optional[str] = None
    fecha_registro: Optional[str] = None
    pdf_tamano_bytes: int = 0
    tiene_anexo: bool = False
    fuente_anexo: Optional[str] = None
    procesado_por: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenciaListResponse(BaseModel):
    items: List[EvidenciaItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    q: str


class ProcesarEvidenciasResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    mensaje: Optional[str] = None
    candidatos: int = 0
    revisados: int = 0
    guardados: int = 0
    omitidos: int = 0
    ya_existentes: int = 0
    sin_correo: int = 0
    sin_pdf: int = 0
    etiquetas_faltantes: List[str] = []
    truncado: bool = False


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _to_item(row) -> EvidenciaItem:
    return EvidenciaItem(
        id=row.id,
        gmail_message_id=row.gmail_message_id,
        gmail_thread_id=row.gmail_thread_id,
        etiqueta_gmail=row.etiqueta_gmail,
        email_cliente=row.email_cliente,
        cedula=row.cedula,
        asunto=row.asunto,
        fecha_mensaje=_iso(row.fecha_mensaje),
        fecha_registro=_iso(row.fecha_registro),
        pdf_tamano_bytes=int(row.pdf_tamano_bytes or 0),
        tiene_anexo=bool(row.tiene_anexo),
        fuente_anexo=row.fuente_anexo,
        procesado_por=row.procesado_por,
    )


@router.post("/escanear", response_model=ProcesarEvidenciasResponse)
def escanear_evidencias(
    max_messages: int = Query(40, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    """Escaneo manual: etiquetas DIA SIGUIENTE / 1 CUOTA / 2 O MAS CUOTAS -> PDF en BD."""
    result = svc.procesar_evidencias_gmail(
        db,
        procesado_por=(getattr(admin, "email", None) or getattr(admin, "username", None) or "admin"),
        max_messages=max_messages,
        presupuesto_segundos=50.0,
    )
    return ProcesarEvidenciasResponse(**result)


@router.get("", response_model=EvidenciaListResponse)
def listar_evidencias(
    q: str = Query(..., min_length=2, description="Cedula o email del cliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    skip = (page - 1) * page_size
    rows, total = svc.buscar_evidencias(db, q=q, skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return EvidenciaListResponse(
        items=[_to_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        q=q,
    )


@router.get("/{evidencia_id}/pdf")
def descargar_pdf_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    row = svc.obtener_pdf(db, evidencia_id)
    if row is None or not row.pdf_contenido:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    safe_email = (row.email_cliente_norm or "cliente").replace("@", "_at_")[:40]
    etiqueta = (row.etiqueta_gmail or "evidencia").replace(" ", "_")
    filename = f"evidencia_{etiqueta}_{safe_email}_{row.id}.pdf"
    return Response(
        content=bytes(row.pdf_contenido),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
