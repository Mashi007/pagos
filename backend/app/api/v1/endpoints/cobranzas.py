"""
Endpoints de cobranzas (stub para que el frontend no reciba 404).
Estructura de respuestas compatible con cobranzasService.ts.
Cuando exista conexión a BD (get_db/Session), reemplazar respuestas stub por consultas reales.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

router = APIRouter()


# ---------------------------------------------------------------------------
# Resumen y diagnóstico
# ---------------------------------------------------------------------------

@router.get("/resumen")
def get_resumen(incluir_admin: bool = Query(False), incluir_diagnostico: bool = Query(False)):
    """Resumen de cobranzas: total cuotas vencidas, monto adeudado, clientes atrasados."""
    data: dict[str, Any] = {
        "total_cuotas_vencidas": 0,
        "monto_total_adeudado": 0,
        "clientes_atrasados": 0,
    }
    if incluir_diagnostico:
        data["diagnosticos"] = _stub_diagnostico()
    return data


@router.get("/diagnostico")
def get_diagnostico():
    """Diagnóstico completo de cobranzas (cuotas BD, vencidas, filtros)."""
    return {
        "diagnosticos": _stub_diagnostico(),
        "analisis_filtros": {
            "cuotas_perdidas_por_estado": 0,
            "cuotas_perdidas_por_admin": 0,
            "cuotas_perdidas_por_user_admin": 0,
        },
    }


def _stub_diagnostico() -> dict[str, Any]:
    return {
        "total_cuotas_bd": 0,
        "cuotas_vencidas_solo_fecha": 0,
        "cuotas_pago_incompleto": 0,
        "cuotas_vencidas_incompletas": 0,
        "estados_prestamos_con_cuotas_vencidas": {},
    }


# ---------------------------------------------------------------------------
# Clientes atrasados
# ---------------------------------------------------------------------------

@router.get("/clientes-atrasados")
def get_clientes_atrasados(
    dias_retraso: Optional[int] = Query(None),
    dias_retraso_min: Optional[int] = Query(None),
    dias_retraso_max: Optional[int] = Query(None),
    incluir_admin: bool = Query(False),
    incluir_ml: bool = Query(True),
):
    """Lista de clientes con cuotas atrasadas. Front acepta array o { clientes_atrasados: [] }."""
    return []


@router.get("/clientes-por-cantidad-pagos")
def get_clientes_por_cantidad_pagos(cantidad_pagos: int = Query(...)):
    """Clientes con exactamente N pagos atrasados."""
    return []


# ---------------------------------------------------------------------------
# Por analista
# ---------------------------------------------------------------------------

@router.get("/por-analista")
def get_cobranzas_por_analista(incluir_admin: bool = Query(False)):
    """Cobranzas agrupadas por analista: nombre, cantidad_clientes, monto_total."""
    return []


@router.get("/por-analista/{analista}/clientes")
def get_clientes_por_analista(analista: str):
    """Clientes atrasados de un analista (analista puede ser nombre o email)."""
    return []


# ---------------------------------------------------------------------------
# Montos por mes
# ---------------------------------------------------------------------------

@router.get("/montos-por-mes")
def get_montos_por_mes(incluir_admin: bool = Query(False)):
    """Montos vencidos por mes. Front espera [{ mes, mes_display, cantidad_cuotas, monto_total }]."""
    return []


# ---------------------------------------------------------------------------
# Informes (JSON / PDF / Excel)
# ---------------------------------------------------------------------------

@router.get("/informes/clientes-atrasados")
def get_informe_clientes_atrasados(
    dias_retraso_min: Optional[int] = Query(None),
    dias_retraso_max: Optional[int] = Query(None),
    analista: Optional[str] = Query(None),
    formato: Optional[str] = Query("json"),
):
    """Informe clientes atrasados. formato=json|pdf|excel."""
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return {"clientes": [], "resumen": {}}


@router.get("/informes/rendimiento-analista")
def get_informe_rendimiento_analista(formato: str = Query("json")):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return []


@router.get("/informes/montos-vencidos-periodo")
def get_informe_montos_periodo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    formato: Optional[str] = Query("json"),
):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return []


@router.get("/informes/antiguedad-saldos")
def get_informe_antiguedad_saldos(formato: str = Query("json")):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return []


@router.get("/informes/resumen-ejecutivo")
def get_informe_resumen_ejecutivo(formato: str = Query("json")):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return {}


# ---------------------------------------------------------------------------
# Notificaciones y ML
# ---------------------------------------------------------------------------

@router.post("/notificaciones/atrasos")
def procesar_notificaciones_atrasos():
    """Procesar y enviar notificaciones de atrasos."""
    return {"mensaje": "Procesamiento de notificaciones (stub).", "estadisticas": {}}


@router.put("/prestamos/{prestamo_id}/ml-impago")
def actualizar_ml_impago(prestamo_id: int, body: dict):
    """Marcar ML impago manual: nivel_riesgo, probabilidad_impago."""
    return {"ok": True, "prestamo_id": prestamo_id}


@router.delete("/prestamos/{prestamo_id}/ml-impago")
def eliminar_ml_impago_manual(prestamo_id: int):
    """Quitar ML impago manual y volver a valores calculados."""
    return {"ok": True, "prestamo_id": prestamo_id}
