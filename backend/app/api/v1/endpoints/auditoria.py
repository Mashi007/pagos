"""
Endpoints de auditoría (stub para que el frontend no reciba 404).
GET listado, GET stats, GET exportar, GET /{id}, POST /registrar.

Conexión a BD (cuando exista):
- Inyectar sesión: def listar_auditoria(..., db: Session = Depends(get_db))
- Crear modelo/tabla auditoria y consultar con db.query(AuditoriaModel).filter(...)
- Validar y sanear parámetros de query (usuario_email, modulo, fechas) antes de usarlos en la consulta
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


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
):
    """
    Lista registros de auditoría con filtros y paginación.
    Stub: devuelve lista vacía hasta tener BD/negocio real.
    """
    # TODO: cuando exista tabla auditoria y sesión BD, filtrar y paginar
    return AuditoriaListResponse(
        items=[],
        total=0,
        page=(skip // limit) + 1 if limit else 1,
        page_size=limit,
        total_pages=0,
    )


@router.get("/stats", response_model=AuditoriaStats)
def obtener_estadisticas():
    """
    Estadísticas de auditoría (totales, por módulo, por usuario, hoy/semana/mes).
    Stub: ceros hasta tener BD real.
    """
    return AuditoriaStats(
        total_acciones=0,
        acciones_por_modulo={},
        acciones_por_usuario={},
        acciones_hoy=0,
        acciones_esta_semana=0,
        acciones_este_mes=0,
    )


@router.get("/exportar")
def exportar_auditoria(
    usuario_email: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
):
    """
    Exporta auditoría a Excel. Stub: devuelve archivo vacío/minimal hasta tener BD.
    El frontend espera responseType blob.
    """
    # Excel mínimo (cabecera XLSX) para que el navegador reciba algo descargable
    minimal_xlsx = (
        b"PK\x03\x04"  # ZIP signature (XLSX es ZIP)
        b"\x14\x00\x00\x00\x08\x00"
        b"[\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    return StreamingResponse(
        iter([minimal_xlsx]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=auditoria_stub.xlsx"},
    )


@router.get("/{auditoria_id}", response_model=AuditoriaItem)
def obtener_auditoria(auditoria_id: int):
    """
    Obtiene un registro de auditoría por ID. Stub: 404 hasta tener BD.
    """
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Registro de auditoría no implementado (stub)")


@router.post("/registrar", response_model=AuditoriaItem)
def registrar_evento(body: RegistrarAuditoriaBody):
    """
    Registra un evento de auditoría (confirmaciones, acciones manuales).
    Stub: acepta el body y devuelve un objeto simulado hasta persistir en BD.
    """
    import datetime
    # Stub: no persiste; cuando haya BD, insertar en tabla auditoria
    return AuditoriaItem(
        id=0,
        usuario_email=None,
        accion=body.accion,
        modulo=body.modulo,
        tabla="",
        descripcion=body.descripcion,
        registro_id=body.registro_id,
        resultado="EXITOSO",
        fecha=datetime.datetime.utcnow().isoformat() + "Z",
    )
