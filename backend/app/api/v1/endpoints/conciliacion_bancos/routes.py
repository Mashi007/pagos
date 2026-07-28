"""Endpoints Conciliacion Bancos (solo admin)."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.conciliacion_banco_ocr import ConciliacionBancoOcrLote
from app.schemas.auth import UserResponse
from app.services import conciliacion_bancos_service as svc

router = APIRouter(
    prefix="/conciliacion-bancos",
    tags=["conciliacion-bancos"],
    dependencies=[Depends(require_admin)],
)


class DecisionBody(BaseModel):
    decision: str = Field(..., description="VISTO | CORREGIR | OMITIR")
    fuente_elegida: Optional[str] = Field(
        None, description="BD | BANCO (requerido si decision=CORREGIR)"
    )
    pago_id_elegido: Optional[int] = Field(
        None,
        description="AMBIGUO+CORREGIR: un pago elegido (compat). Preferir pago_ids_elegidos.",
    )
    pago_ids_elegidos: Optional[List[int]] = Field(
        None,
        description="AMBIGUO+CORREGIR: uno, varios o todos los candidatos a aprobar",
    )


class CompararBody(BaseModel):
    bancos: List[str] = Field(
        default_factory=list,
        description="Categorias: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros",
    )
    fecha_desde: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )
    fecha_hasta: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )


class DecisionMasivaItem(BaseModel):
    resultado_id: int
    fuente_elegida: Optional[str] = None
    pago_id_elegido: Optional[int] = None
    pago_ids_elegidos: Optional[List[int]] = None


class DecisionMasivaBody(BaseModel):
    items: List[DecisionMasivaItem]
    fuente_default: str = Field(
        default="BANCO", description="BD | BANCO si el item no trae fuente"
    )


def _notas_lote(lote: ConciliacionBancoOcrLote) -> dict:
    raw = (lote.notas or "").strip()
    if not raw:
        return {}
    try:
        import json

        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _job_vivo(lote_id: int) -> bool:
    try:
        from app.services.conciliacion_bancos_bg_runner import comparar_activo

        return bool(comparar_activo(int(lote_id)))
    except Exception:
        return False


def _lote_dict(lote: ConciliacionBancoOcrLote, db: Session | None = None) -> dict:
    notas = _notas_lote(lote)
    filas = notas.get("filas_banco")
    stats = notas.get("stats")
    # Tras COMPARADO, KPIs vivos (bajan pendientes / sube CONCILIADOS al confirmar).
    if db is not None and str(lote.estado or "").upper() == "COMPARADO":
        stats = svc.kpis_vivos_lote(db, int(lote.id))
    return {
        "id": lote.id,
        "archivo_nombre": lote.archivo_nombre,
        "fecha_desde": lote.fecha_desde.isoformat() if lote.fecha_desde else None,
        "fecha_hasta": lote.fecha_hasta.isoformat() if lote.fecha_hasta else None,
        "estado": lote.estado,
        "moneda_carga": lote.moneda_carga,
        "usuario_id": lote.usuario_id,
        "creado_en": lote.creado_en.isoformat() if lote.creado_en else None,
        "bancos_filtro": svc._leer_bancos_de_lote(lote),
        "filas_banco": int(filas) if filas is not None else None,
        "stats": stats,
        "pagos_universo": notas.get("pagos_universo"),
        "comparar_elapsed_ms": notas.get("comparar_elapsed_ms"),
        "comparar_error": notas.get("comparar_error"),
        "comparar_huerfano": bool(notas.get("comparar_huerfano")),
        "job_vivo": _job_vivo(lote.id),
        "filas_extracto_upsert": notas.get("filas_extracto_upsert"),
        "extracto_error": notas.get("extracto_error"),
        "fuente_carga": notas.get("fuente_carga"),
    }


class LoteHistoricaBody(BaseModel):
    bancos: List[str] = Field(default_factory=list)
    fecha_desde: date
    fecha_hasta: date
    moneda_carga: str = "USD"


@router.post("/lotes")
async def crear_lote(
    file: UploadFile = File(...),
    moneda_carga: str = Form("USD"),
    fecha_desde: date = Form(...),
    fecha_hasta: date = Form(...),
    banco: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    """Sube Excel (Banco|Fecha|Referencia|Monto). Siempre upsert a BD historica."""
    content = await file.read()
    lote = svc.crear_lote_desde_excel(
        db,
        file=file,
        content=content,
        moneda_carga=moneda_carga,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=getattr(user, "id", None),
        banco=banco,
    )
    return {"ok": True, "lote": _lote_dict(lote)}


class LoteSerialBody(BaseModel):
    serial: str = Field(..., min_length=1, description="Referencia / serial / documento")
    moneda_carga: str = "USD"
    bancos: List[str] = Field(default_factory=list)


@router.post("/lotes/desde-historica")
def crear_lote_historica(
    body: LoteHistoricaBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    """Carga un lote desde conciliacion_banco_extracto (BD historica)."""
    lote = svc.crear_lote_desde_extracto(
        db,
        bancos=body.bancos,
        fecha_desde=body.fecha_desde,
        fecha_hasta=body.fecha_hasta,
        moneda_carga=body.moneda_carga,
        usuario_id=getattr(user, "id", None),
    )
    return {"ok": True, "lote": _lote_dict(lote)}


@router.get("/extracto/por-serial")
def extracto_por_serial(
    serial: str,
    moneda: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    """Responde si el serial esta en BD historica (y si hay pago en pagos)."""
    return svc.buscar_serial_en_extracto(db, serial=serial, moneda=moneda)


@router.post("/lotes/desde-serial")
def crear_lote_serial(
    body: LoteSerialBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    """Si el serial esta en BD historica, crea lote para conciliar."""
    lote = svc.crear_lote_desde_serial(
        db,
        serial=body.serial,
        moneda_carga=body.moneda_carga,
        usuario_id=getattr(user, "id", None),
        bancos=body.bancos or None,
    )
    return {"ok": True, "lote": _lote_dict(lote)}


@router.get("/extracto/resumen")
def extracto_resumen(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    moneda: Optional[str] = None,
    bancos: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    lista = [x.strip() for x in (bancos or "").split(",") if x.strip()]
    return svc.resumen_extracto_historico(
        db,
        bancos=lista or None,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        moneda=moneda,
    )


@router.get("/lotes/{lote_id}")
def obtener_lote(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    lote = db.get(ConciliacionBancoOcrLote, lote_id)
    if not lote:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Lote no encontrado")
    # Polling: si el worker reinicio, no dejar el UI colgado en COMPARANDO.
    svc.sanear_comparando_huerfano(db, lote)
    db.refresh(lote)
    return {"ok": True, "lote": _lote_dict(lote, db)}


@router.post("/lotes/{lote_id}/comparar")
def comparar(
    lote_id: int,
    body: CompararBody = CompararBody(),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    """Inicia comparar en background (lotes grandes ~25k). Polling GET /lotes/{id}."""
    return svc.iniciar_comparar_lote(
        db,
        lote_id,
        bancos_filtro=body.bancos,
        fecha_desde=body.fecha_desde,
        fecha_hasta=body.fecha_hasta,
    )


@router.get("/lotes/{lote_id}/resultados")
def resultados(
    lote_id: int,
    page: int = 1,
    per_page: int = 1000,
    tipo_novedad: Optional[str] = None,
    decision: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    tipos = None
    if tipo_novedad:
        tipos = [x.strip() for x in tipo_novedad.split(",") if x.strip()]
    data = svc.listar_resultados(
        db,
        lote_id,
        page=page,
        per_page=per_page,
        tipos=tipos,
        decision=decision,
    )
    return {"ok": True, **data}


@router.post("/resultados/{resultado_id}/decidir")
def decidir(
    resultado_id: int,
    body: DecisionBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    return svc.decidir_y_aplicar(
        db,
        resultado_id,
        decision=body.decision,
        fuente_elegida=body.fuente_elegida,
        usuario_id=getattr(user, "id", None),
        pago_id_elegido=body.pago_id_elegido,
        pago_ids_elegidos=body.pago_ids_elegidos,
    )


@router.post("/resultados/decidir-masivo")
def decidir_masivo(
    body: DecisionMasivaBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    return svc.decidir_masivo(
        db,
        [i.model_dump() for i in body.items],
        usuario_id=getattr(user, "id", None),
        fuente_default=body.fuente_default,
    )


@router.get("/lotes/{lote_id}/exportar-excel")
def exportar(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    data = svc.exportar_excel_lote(db, lote_id)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="conciliacion_bancos_lote_{lote_id}.xlsx"'
        },
    )