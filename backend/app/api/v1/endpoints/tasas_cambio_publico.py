"""
Endpoints de lectura de tasas para usuarios autenticados (no admin).

No reemplaza ni modifica /admin/tasas-cambio; solo expone GET de consulta
para evitar 403/404 en operadores sin elevar permisos de escritura.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    debe_ingresar_tasa,
    estado_multifuente_fila_hoy,
    fila_tasa_multifuente_completa_hoy,
    obtener_tasa_hoy,
)

# Reusar el mismo contrato de respuesta de /admin/tasas-cambio/hoy
from app.api.v1.endpoints.admin_tasas_cambio.routes import TasaCambioResponse

router = APIRouter(prefix="/tasas-cambio", tags=["tasas-cambio"])


@router.get("/hoy", response_model=Optional[TasaCambioResponse])
def get_tasa_hoy_publico(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Lectura de tasa para hoy (usuarios autenticados).
    """
    _ = current_user
    return obtener_tasa_hoy(db)


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
    debe_ingresar = debe_ingresar_tasa()
    tasa_guardada = obtener_tasa_hoy(db)
    mf = estado_multifuente_fila_hoy(tasa_guardada)
    completa = fila_tasa_multifuente_completa_hoy(tasa_guardada)

    return {
        "debe_ingresar": debe_ingresar,
        "tasa_ya_ingresada": completa,
        "euro_ok": mf["euro_ok"],
        "bcv_ok": mf["bcv_ok"],
        "binance_ok": mf["binance_ok"],
        "hora_obligatoria_desde": "01:00",
        "hora_obligatoria_hasta": "23:59",
    }

