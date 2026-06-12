"""Esquemas API Finiquito."""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FiniquitoRegistroRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr


class FiniquitoRegistroResponse(BaseModel):
    ok: bool
    message: str


class FiniquitoSolicitarCodigoRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr


class FiniquitoSolicitarCodigoResponse(BaseModel):
    ok: bool
    message: str


class FiniquitoVerificarCodigoRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    codigo: str = Field(..., min_length=4, max_length=10)


class FiniquitoVerificarCodigoResponse(BaseModel):
    ok: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    error: Optional[str] = None


class FiniquitoCasoOut(BaseModel):
    id: int
    prestamo_id: int
    cliente_id: Optional[int]
    cedula: str
    total_financiamiento: str
    sum_total_pagado: str
    estado: str
    ultimo_refresh_utc: Optional[str] = None
    ultima_fecha_pago: Optional[str] = Field(
        default=None,
        description="Ultima fecha_pago en tabla pagos para este prestamo_id (MAX).",
    )
    contacto_para_siguientes: Optional[bool] = Field(
        default=None,
        description="Si estado=TERMINADO: respuesta Sí/No a contacto para pasos siguientes.",
    )
    cliente_nombres: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None
    finiquito_tramite_fecha_limite: Optional[str] = Field(
        default=None,
        description=(
            "Desde prestamos: fin del ciclo finiquito (dia 30 desde creado_en del caso), ISO date."
        ),
    )
    fecha_liquidado: Optional[str] = Field(
        default=None,
        description="Desde prestamos: fecha calendario en que el prestamo paso a LIQUIDADO.",
    )
    creado_en: Optional[str] = Field(
        default=None,
        description="Alta del caso en finiquito_casos (materializacion), ISO datetime UTC.",
    )
    fecha_entrada_en_proceso: Optional[str] = Field(
        default=None,
        description=(
            "Desde historial: ultima vez que el caso paso a EN_PROCESO (area de trabajo), ISO datetime."
        ),
    )
    fecha_entrada_aceptado: Optional[str] = Field(
        default=None,
        description=(
            "Desde historial: ultima vez que el caso paso a ACEPTADO (area de revision), ISO datetime."
        ),
    )
    conciliacion_visto_activa: Optional[bool] = Field(
        default=None,
        description="True si hay reserva temporal de comprobantes (flujo Visto en curso).",
    )

    model_config = ConfigDict(from_attributes=True)


class FiniquitoConteoRevisionNuevosResponse(BaseModel):
    """Casos en bandeja principal creados recientemente (al materializarse como LIQUIDADO elegible)."""

    total: int = Field(
        ...,
        ge=0,
        description="Cantidad en bandeja principal dentro de la ventana temporal.",
    )
    ventana_horas: int = Field(
        ...,
        ge=1,
        description="Horas hacia atras desde ahora (UTC) usadas en el conteo.",
    )


class FiniquitoAdminResumenEstadoResponse(BaseModel):
    """Snapshot liviano para detectar cambios sin recargar listas completas."""

    total: int = Field(..., ge=0)
    revision: int = Field(..., ge=0)
    aceptado: int = Field(..., ge=0)
    rechazado: int = Field(..., ge=0)
    en_proceso: int = Field(..., ge=0)
    terminado: int = Field(..., ge=0)
    max_ultimo_refresh_utc: Optional[str] = Field(
        default=None,
        description="MAX(ultimo_refresh_utc) de la vista filtrada.",
    )
    max_creado_en_utc: Optional[str] = Field(
        default=None,
        description="MAX(creado_en) de la vista filtrada.",
    )


class FiniquitoCasoListaResponse(BaseModel):
    items: List[FiniquitoCasoOut]
    total: int = Field(
        ...,
        description="Total de filas que coinciden con el filtro (sin paginar).",
    )
    limit: int = Field(
        ...,
        description="Tamano de pagina efectivo (admin) o filas devueltas (publico sin paginar).",
    )
    offset: int = Field(..., description="Desplazamiento desde el mas reciente (orden id desc).")


class FiniquitoEliminarCasoResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class FiniquitoLiberarProcesosNormalesResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    prestamo_id: Optional[int] = None
    estado_prestamo_antes: Optional[str] = None
    estado_prestamo_despues: Optional[str] = None
    forzado_aprobado: Optional[bool] = None
    mensaje: Optional[str] = None


class FiniquitoPatchEstadoRequest(BaseModel):
    estado: str = Field(
        ...,
        description=(
            "REVISION (bandeja) | ACEPTADO (validado, area de revision) | "
            "RECHAZADO | EN_PROCESO (area de trabajo) | TERMINADO"
        ),
    )
    contacto_para_siguientes: Optional[bool] = Field(
        None,
        description=(
            "Al pasar a TERMINADO: obligatorio si venia de EN_PROCESO; "
            "opcional si venia de ACEPTADO (por defecto false)."
        ),
    )

class FiniquitoPatchEstadoResponse(BaseModel):
    ok: bool
    caso: Optional[FiniquitoCasoOut] = None
    error: Optional[str] = None


class FiniquitoDetalleResponse(BaseModel):
    caso: FiniquitoCasoOut
    prestamo: Optional[dict[str, Any]] = None
    cuotas: Optional[List[dict[str, Any]]] = None


class FiniquitoTerminadoItemOut(BaseModel):
    """Caso en estado TERMINADO con fechas de prestamo e historial."""

    id: int
    prestamo_id: int
    cedula: str
    nombre: str
    total_financiamiento: str
    fecha_aprobacion: Optional[str] = Field(
        default=None,
        description="Desde prestamos.fecha_aprobacion (ISO).",
    )
    fecha_termino_pago: Optional[str] = Field(
        default=None,
        description="Ultima fecha_pago en pagos para el prestamo (ISO date).",
    )
    fecha_terminado: Optional[str] = Field(
        default=None,
        description="Fecha en que el caso paso a TERMINADO (historial de estados).",
    )
    contacto_para_siguientes: Optional[bool] = None


class FiniquitoTerminadosListaResponse(BaseModel):
    items: List[FiniquitoTerminadoItemOut]
    total: int
    limit: int
    offset: int


class FiniquitoTerminadosSemanaOut(BaseModel):
    """Conteo de casos terminados agrupados por semana ISO (lunes)."""

    semana: str = Field(..., description="Clave ISO, ej. 2026-W20")
    etiqueta: str = Field(..., description="Etiqueta corta para grafico, ej. Sem 20 · 2026")
    cantidad: int = Field(..., ge=0)


class FiniquitoTerminadosResumenSemanalResponse(BaseModel):
    semanas: List[FiniquitoTerminadosSemanaOut]
    total_terminados: int = Field(..., ge=0)


class FiniquitoTerminadosDiaOut(BaseModel):
    """Conteo de casos terminados agrupados por dia calendario (America/Caracas)."""

    fecha: str = Field(..., description="YYYY-MM-DD en calendario Caracas")
    etiqueta: str = Field(..., description="Etiqueta corta para grafico, ej. Hoy, Ayer, 12/06")
    cantidad: int = Field(..., ge=0)


class FiniquitoTerminadosResumenDiarioResponse(BaseModel):
    dias: List[FiniquitoTerminadosDiaOut]
    total_terminados: int = Field(
        ...,
        ge=0,
        description="Total casos TERMINADO que coinciden con el filtro de cedula (sin acotar ventana).",
    )
    total_en_ventana: int = Field(
        ...,
        ge=0,
        description="Suma de cantidades en la ventana diaria devuelta.",
    )


class FiniquitoConciliacionVistoIniciarRequest(BaseModel):
    confirmar_sin_comprobantes: bool = Field(
        False,
        description=(
            "Si no hay comprobantes reservables, continuar tras confirmación del usuario "
            "(borra pagos si existen y abre revisión manual)."
        ),
    )


class FiniquitoConciliacionVistoIniciarResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    ya_iniciado: Optional[bool] = None
    reservas: Optional[int] = None
    pagos_eliminados: Optional[int] = None
    mensaje: Optional[str] = None


class FiniquitoConciliacionRecrearOcrItem(BaseModel):
    reserva_id: int
    ok: bool
    error: Optional[str] = None
    pago_id: Optional[int] = None


class FiniquitoConciliacionRecrearOcrResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    total: Optional[int] = None
    ocr_ok: Optional[int] = None
    ocr_fallidos: Optional[int] = None
    pagos_recriados: Optional[int] = None
    mensaje: Optional[str] = None
    detalle: Optional[List[FiniquitoConciliacionRecrearOcrItem]] = None
    cascada: Optional[dict[str, Any]] = None


class FiniquitoConciliacionPasarATrabajoResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    caso: Optional[FiniquitoCasoOut] = None
    reservas_eliminadas: Optional[int] = None
