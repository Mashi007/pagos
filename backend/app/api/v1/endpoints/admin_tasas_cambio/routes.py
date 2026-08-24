"""
Endpoints para administrar tasas de cambio oficial (admin).
"""
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_utils import user_is_administrator
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    actualizar_una_tasa_en_fecha,
    construir_payload_estado_tasa,
    es_fin_de_semana_caracas,
    estado_multifuente_fila_hoy,
    fecha_hoy_caracas,
    fila_tasa_multifuente_completa_hoy,
    guardar_tasa_diaria,
    guardar_tasa_para_fecha,
    listar_tasas_problematicas,
    obtener_tasa_hoy,
    obtener_tasa_por_fecha,
    rellenar_tasas_problematicas_desde_vecino,
    ultimo_viernes_anterior,
)

router = APIRouter(prefix="/admin/tasas-cambio", tags=["admin-tasas-cambio"])


class TasaCambioResponse(BaseModel):
    """Respuesta API: fechas como string ISO (el ORM entrega datetime)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    tasa_oficial: float
    tasa_bcv: Optional[float] = None
    tasa_binance: Optional[float] = None
    usuario_email: Optional[str] = None
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def coerce_datetime_to_iso(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, str):
            return v
        raise ValueError("created_at/updated_at must be datetime or str")

    @field_validator("tasa_bcv", "tasa_binance", mode="before")
    @classmethod
    def coerce_optional_numeric(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        return float(v)


class GuardarTasaRequest(BaseModel):
    tasa_oficial: float = Field(..., gt=0, description="Euro: Bs. por 1 USD (columna tasa_oficial)")
    tasa_bcv: Optional[float] = Field(default=None, gt=0, description="BCV: Bs. por 1 USD (opcional; el bot la llena)")
    tasa_binance: Optional[float] = Field(default=None, gt=0, description="Histórico; ya no se pide en UI")


class GuardarTasaPorFechaRequest(BaseModel):
    """Backfill: tasa para una fecha de pago (no aplica ventana 01:00 de guardar/hoy)."""

    fecha: date = Field(..., description="Fecha calendario YYYY-MM-DD (fecha_pago del reporte)")
    tasa_oficial: float = Field(..., gt=0, description="Euro: Bs. por 1 USD (valor por defecto del sistema)")
    tasa_bcv: Optional[float] = Field(default=None, description="BCV: Bs. por 1 USD (opcional)")
    tasa_binance: Optional[float] = Field(default=None, description="Binance P2P: Bs. por 1 USD (opcional)")


class EditarUnaTasaRequest(BaseModel):
    """Edita una sola columna (Euro, BCV o Binance) en una fecha."""

    fecha: date = Field(..., description="Fecha calendario YYYY-MM-DD")
    fuente: str = Field(..., description="euro | bcv | binance")
    valor: float = Field(..., gt=0, description="Bs. por 1 USD")


class RellenarTasasDesdeVecinoBody(BaseModel):
    """Simula o aplica copia de tasa desde la fecha valida mas cercana en BD."""

    dry_run: bool = Field(
        True,
        description="Si true, solo devuelve propuesta sin escribir en BD.",
    )


@router.get("/hoy", response_model=Optional[TasaCambioResponse])
def get_tasa_hoy(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene la tasa de cambio para hoy."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    tasa = obtener_tasa_hoy(db)
    return tasa


@router.get("/estado")
def get_estado_tasa(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Verifica si es necesario ingresar la tasa y devuelve el estado."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    return construir_payload_estado_tasa(db, current_user.email)


@router.post("/capturar-bcv-widget")
def capturar_bcv_widget_endpoint(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Captura manual: un GET al recuadro USD de bcv.org.ve.
    A diferencia del cron, siempre intenta (aunque sea fin de semana o ya haya BCV).
    """
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    from app.services.bcv_widget_tasa_service import (
        BcvWidgetTasaError,
        intentar_captura_bcv_desde_widget,
    )

    try:
        return intentar_captura_bcv_desde_widget(
            db,
            omitir_fin_de_semana=False,
            omitir_si_ya_hay_bcv=False,
        )
    except BcvWidgetTasaError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/guardar", response_model=TasaCambioResponse)
def guardar_tasa(
    req: GuardarTasaRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Guarda Euro (y opcionalmente BCV) para hoy. BCV también lo llena el job automático."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    if es_fin_de_semana_caracas():
        raise HTTPException(
            status_code=400,
            detail=(
                "Sábado y domingo no requieren ingreso manual de tasas: "
                "se copian automáticamente del viernes anterior."
            ),
        )

    db_user = db.query(User).filter(User.email == current_user.email).first()
    usuario_id = db_user.id if db_user else None
    usuario_email = current_user.email

    try:
        tasa = guardar_tasa_diaria(
            db=db,
            tasa_oficial=req.tasa_oficial,
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            tasa_bcv=req.tasa_bcv,
            tasa_binance=req.tasa_binance,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return tasa


@router.post("/guardar-por-fecha", response_model=TasaCambioResponse)
def guardar_tasa_por_fecha_endpoint(
    req: GuardarTasaPorFechaRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Inserta o actualiza la tasa oficial para una fecha arbitraria.
    Administradores: útil para registrar tasas faltantes al corregir pagos BS históricos.
    """
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    db_user = db.query(User).filter(User.email == current_user.email).first()
    usuario_id = db_user.id if db_user else None
    usuario_email = current_user.email

    try:
        tasa = guardar_tasa_para_fecha(
            db=db,
            fecha=req.fecha,
            tasa_oficial=req.tasa_oficial,
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            tasa_bcv=req.tasa_bcv,
            tasa_binance=req.tasa_binance,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return tasa


@router.post("/editar-una", response_model=TasaCambioResponse)
def editar_una_tasa_endpoint(
    req: EditarUnaTasaRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Actualiza solo Euro, BCV o Binance en la fecha indicada. No pisa las otras."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    db_user = db.query(User).filter(User.email == current_user.email).first()
    try:
        return actualizar_una_tasa_en_fecha(
            db,
            fecha=req.fecha,
            fuente=req.fuente,
            valor=req.valor,
            usuario_id=db_user.id if db_user else None,
            usuario_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/tasas-problematicas")
def get_tasas_problematicas(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Lista filas con tasa <= 0 o valor tipo placeholder (99999.99 de plantillas).
    Usar antes de rellenar desde vecino o para auditoria.
    """
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    rows = listar_tasas_problematicas(db)
    return {
        "total": len(rows),
        "filas": [
            {
                "fecha": r.fecha.isoformat(),
                "tasa_oficial": float(r.tasa_oficial) if r.tasa_oficial is not None else None,
                "usuario_email": r.usuario_email,
            }
            for r in rows
        ],
    }


@router.post("/rellenar-desde-vecino")
def post_rellenar_tasas_desde_vecino(
    body: RellenarTasasDesdeVecinoBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Para tasas problematicas, asigna la tasa de la fecha valida mas cercana en la misma tabla.
    Por defecto dry_run=true. Revise el resultado y ejecute con dry_run=false para persistir.
    """
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    email = (current_user.email or "admin").strip() or "admin"
    return rellenar_tasas_problematicas_desde_vecino(
        db,
        dry_run=body.dry_run,
        usuario_email=email,
    )


@router.get("/por-fecha", response_model=Optional[TasaCambioResponse])
def get_tasa_por_fecha(
    fecha: date = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene la tasa de cambio para una fecha especifica."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    tasa = obtener_tasa_por_fecha(db, fecha)
    return tasa


@router.get("/historial")
def get_historial_tasas(
    limite: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene el historial de tasas (ultimas N fechas)."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    from sqlalchemy import desc

    tasas = (
        db.query(TasaCambioDiaria)
        .order_by(desc(TasaCambioDiaria.fecha))
        .limit(limite)
        .all()
    )

    return [
        {
            "id": t.id,
            "fecha": t.fecha.isoformat(),
            "tasa_oficial": float(t.tasa_oficial),
            "tasa_bcv": float(t.tasa_bcv) if getattr(t, "tasa_bcv", None) is not None else None,
            "tasa_binance": float(t.tasa_binance) if getattr(t, "tasa_binance", None) is not None else None,
            "usuario_email": t.usuario_email,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in tasas
    ]
