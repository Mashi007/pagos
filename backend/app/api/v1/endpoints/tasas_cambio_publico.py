"""
Endpoints de lectura de tasas para usuarios autenticados (no admin).

No reemplaza ni modifica /admin/tasas-cambio; solo expone GET de consulta
para evitar 403/404 en operadores sin elevar permisos de escritura.
"""
import threading
import time
from datetime import date
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    construir_payload_estado_tasa,
    obtener_tasa_hoy,
    obtener_tasa_por_fecha,
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


@router.get("/por-fecha", response_model=Optional[TasaCambioResponse])
def get_tasa_por_fecha_publico(
    fecha: date = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Lectura de tasa por fecha (usuarios autenticados). Evita 404 ruidoso del fallback admin."""
    _ = current_user
    return obtener_tasa_por_fecha(db, fecha)


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
    return construir_payload_estado_tasa(db, current_user.email)

