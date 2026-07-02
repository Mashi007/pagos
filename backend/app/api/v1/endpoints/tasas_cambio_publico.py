"""
Endpoints de lectura de tasas para usuarios autenticados (no admin).

No reemplaza ni modifica /admin/tasas-cambio; solo expone GET de consulta
para evitar 403/404 en operadores sin elevar permisos de escritura.
"""
import threading
import time
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    debe_ingresar_tasa,
    es_fin_de_semana_caracas,
    estado_multifuente_fila_hoy,
    fecha_hoy_caracas,
    fila_tasa_multifuente_completa_hoy,
    obtener_tasa_hoy,
    ultimo_viernes_anterior,
)

# Reusar el mismo contrato de respuesta de /admin/tasas-cambio/hoy
from app.api.v1.endpoints.admin_tasas_cambio.routes import TasaCambioResponse

router = APIRouter(prefix="/tasas-cambio", tags=["tasas-cambio"])

_TASA_READ_CACHE_TTL_SEC = 60.0
_tasa_read_cache: dict[str, tuple[float, Any]] = {}
_tasa_read_cache_lock = threading.Lock()


def _tasa_read_cached(key: str, builder: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _tasa_read_cache_lock:
        hit = _tasa_read_cache.get(key)
        if hit is not None and now - hit[0] < _TASA_READ_CACHE_TTL_SEC:
            return hit[1]
    data = builder()
    with _tasa_read_cache_lock:
        _tasa_read_cache[key] = (now, data)
    return data


def _build_estado_tasa_payload(db: Session) -> dict:
    debe_ingresar = debe_ingresar_tasa()
    tasa_guardada = obtener_tasa_hoy(db)
    mf = estado_multifuente_fila_hoy(tasa_guardada)
    completa = fila_tasa_multifuente_completa_hoy(tasa_guardada)
    hoy = fecha_hoy_caracas()
    fin_de_semana = es_fin_de_semana_caracas(hoy)

    return {
        "debe_ingresar": debe_ingresar,
        "tasa_ya_ingresada": completa,
        "euro_ok": mf["euro_ok"],
        "bcv_ok": mf["bcv_ok"],
        "binance_ok": mf["binance_ok"],
        "hora_obligatoria_desde": "01:00",
        "hora_obligatoria_hasta": "23:59",
        "fin_de_semana_caracas": fin_de_semana,
        "fecha_referencia_viernes": (
            ultimo_viernes_anterior(hoy).isoformat() if fin_de_semana else None
        ),
    }


@router.get("/hoy", response_model=Optional[TasaCambioResponse])
def get_tasa_hoy_publico(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Lectura de tasa para hoy (usuarios autenticados).
    """
    _ = current_user
    return _tasa_read_cached("hoy", lambda: obtener_tasa_hoy(db))


@router.get("/estado")
def get_estado_tasa_publico(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Estado de obligatoriedad/multifuente para hoy (usuarios autenticados).
    Mantiene el mismo shape que /admin/tasas-cambio/estado.
    """
    _ = current_user
    return _tasa_read_cached("estado", lambda: _build_estado_tasa_payload(db))

