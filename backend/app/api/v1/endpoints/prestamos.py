import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.prestamo_auditoria import PrestamoAuditoria
from app.models.user import User
from app.schemas.prestamo import (
    PrestamoCreate,
    PrestamoResponse,
    PrestamoUpdate,
)
from app.services.prestamo_amortizacion_service import (
    generar_tabla_amortizacion as generar_amortizacion,
)
from app.services.prestamo_evaluacion_service import crear_evaluacion_prestamo

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# FUNCIONES AUXILIARES
# ============================================
def calcular_cuotas(
    total: Decimal, modalidad: str, plazo_maximo_meses: Optional[int] = None
) -> tuple[int, Decimal]:
    """
    Calcula el número de cuotas según la modalidad de pago.

    Si hay plazo_maximo (después de evaluación de riesgo), lo utiliza.
    Si no hay plazo_maximo (DRAFT), usa valores por defecto.

    TABLA 12: AJUSTE DE FRECUENCIA DE PAGO
    - MENSUAL: 36 cuotas por defecto
    - QUINCENAL: 72 cuotas por defecto (36 * 2)
    - SEMANAL: 144 cuotas por defecto (36 * 4)

    Si hay plazo_maximo_meses (después de evaluación):
    - MENSUAL: plazo_maximo_meses cuotas
    - QUINCENAL: plazo_maximo_meses * 2 cuotas
    - SEMANAL: plazo_maximo_meses * 4 cuotas
    """
    # Si hay evaluación de riesgo, usar plazo máximo
    if plazo_maximo_meses is not None:
        if modalidad == "MENSUAL":
            cuotas = plazo_maximo_meses
        elif modalidad == "QUINCENAL":
            cuotas = plazo_maximo_meses * 2
        elif modalidad == "SEMANAL":
            cuotas = plazo_maximo_meses * 4
        else:
            cuotas = plazo_maximo_meses
    else:
        # Valores por defecto para DRAFT (antes de evaluación)
        if modalidad == "MENSUAL":
            cuotas = 36
        elif modalidad == "QUINCENAL":
            cuotas = 72
        elif modalidad == "SEMANAL":
            cuotas = 144
        else:
            cuotas = 36  # Default

    cuota_periodo = total / Decimal(cuotas)
    return cuotas, cuota_periodo


def obtener_datos_cliente(cedula: str, db: Session) -> Optional[Cliente]:
    """Obtiene los datos del cliente por cédula"""
    return db.query(Cliente).filter(Cliente.cedula == cedula).first()


def verificar_permisos_edicion(prestamo: Prestamo, current_user: User):
    """Verifica si el usuario tiene permisos para editar el préstamo"""
    if prestamo.estado in ["APROBADO", "RECHAZADO"]:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden editar préstamos aprobados/rechazados",
            )


def puede_cambiar_estado(
    prestamo: Prestamo, nuevo_estado: str, current_user: User
) -> bool:
    """Verifica si el usuario puede cambiar el estado del préstamo"""
    return current_user.is_admin or (
        prestamo.estado == "DRAFT" and nuevo_estado == "EN_REVISION"
    )


def aplicar_cambios_prestamo(prestamo: Prestamo, prestamo_data: PrestamoUpdate):
    """Aplica los cambios del prestamo_data al prestamo"""
    if prestamo_data.total_financiamiento is not None:
        actualizar_monto_y_cuotas(prestamo, prestamo_data.total_financiamiento)

    if prestamo_data.modalidad_pago is not None:
        prestamo.modalidad_pago = prestamo_data.modalidad_pago
        prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(
            prestamo.total_financiamiento, prestamo.modalidad_pago
        )

    if prestamo_data.observaciones is not None:
        prestamo.observaciones = prestamo_data.observaciones


def actualizar_monto_y_cuotas(prestamo: Prestamo, monto: Decimal):
    """Actualiza monto y recalcula cuotas"""
    prestamo.total_financiamiento = monto
    prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(
        prestamo.total_financiamiento, prestamo.modalidad_pago
    )


def procesar_cambio_estado(
    prestamo: Prestamo,
    nuevo_estado: str,
    current_user: User,
    db: Session,
    plazo_maximo_meses: Optional[int] = None,
    tasa_interes: Optional[Decimal] = None,
    fecha_base_calculo: Optional = None,
):
    """Procesa el cambio de estado del préstamo"""
    from datetime import datetime

    estado_anterior = prestamo.estado
    prestamo.estado = nuevo_estado

    if nuevo_estado == "APROBADO":
        prestamo.usuario_aprobador = current_user.email
        prestamo.fecha_aprobacion = datetime.now()

        # Aplicar condiciones desde evaluación de riesgo (FASE 2)
        if plazo_maximo_meses:
            numero_cuotas, cuota_periodo = actualizar_cuotas_segun_plazo_maximo(
                prestamo, plazo_maximo_meses, db
            )
            logger.info(
                f"Cuotas ajustadas según análisis de riesgo: {numero_cuotas} cuotas"
            )

        # Aplicar tasa de interés desde evaluación
        if tasa_interes:
            prestamo.tasa_interes = tasa_interes

        # Aplicar fecha base de cálculo
        if fecha_base_calculo:
            prestamo.fecha_base_calculo = fecha_base_calculo

        # Si se aprueba y tiene fecha_base_calculo, generar tabla de amortización
        if prestamo.fecha_base_calculo:
            try:
                generar_amortizacion(prestamo, prestamo.fecha_base_calculo, db)
                logger.info(
                    f"Tabla de amortización generada para préstamo {prestamo.id}"
                )
            except Exception as e:
                logger.error(f"Error generando amortización: {str(e)}")
                # No fallar el préstamo si falla la generación de cuotas

        # Crear registro automático en Aprobaciones (conectado por cédula)
        try:
            from app.models.aprobacion import Aprobacion

            aprobacion = Aprobacion(
                solicitante_id=current_user.id,
                revisor_id=current_user.id,
                tipo_solicitud="PRESTAMO",
                entidad="Cliente",
                entidad_id=prestamo.cliente_id,
                justificacion=f"Préstamo aprobado para {prestamo.nombres} (Cédula: {prestamo.cedula}). Monto: ${prestamo.total_financiamiento}, Cuotas: {prestamo.numero_cuotas}",
                estado="APROBADA",
                resultado=f"Préstamo #{prestamo.id} aprobado por {current_user.email}",
                fecha_aprobacion=datetime.now(),
                prioridad="NORMAL",
            )
            db.add(aprobacion)
            logger.info(f"Registro de aprobación creado para préstamo {prestamo.id}")
        except Exception as e:
            logger.error(f"Error creando registro de aprobación: {str(e)}")
            # No fallar el préstamo si falla la creación de aprobación

    crear_registro_auditoria(
        prestamo_id=prestamo.id,
        cedula=prestamo.cedula,
        usuario=current_user.email,
        campo_modificado="estado",
        valor_anterior=estado_anterior,
        valor_nuevo=nuevo_estado,
        accion="CAMBIO_ESTADO",
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        db=db,
    )


def crear_registro_auditoria(
    prestamo_id: int,
    cedula: str,
    usuario: str,
    campo_modificado: str,
    valor_anterior: str,
    valor_nuevo: str,
    accion: str,
    estado_anterior: Optional[str] = None,
    estado_nuevo: Optional[str] = None,
    observaciones: Optional[str] = None,
    db: Session = None,
):
    """Crea un registro de auditoría para trazabilidad"""
    auditoria = PrestamoAuditoria(
        prestamo_id=prestamo_id,
        cedula=cedula,
        usuario=usuario,
        campo_modificado=campo_modificado,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        accion=accion,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        observaciones=observaciones,
    )
    db.add(auditoria)
    db.commit()
    db.refresh(auditoria)
    return auditoria


# ============================================
# ENDPOINTS
# ============================================
@router.get("/stats")
def obtener_estadisticas_prestamos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas de préstamos"""
    try:
        total_prestamos = db.query(Prestamo).count()
        prestamos_por_estado = (
            db.query(Prestamo.estado, db.func.count(Prestamo.id))
            .group_by(Prestamo.estado)
            .all()
        )
        
        total_financiado = db.query(
            db.func.sum(Prestamo.total_financiamiento)
        ).scalar() or Decimal("0.00")
        
        return {
            "total_prestamos": total_prestamos,
            "prestamos_por_estado": {estado: count for estado, count in prestamos_por_estado},
            "total_financiado": float(total_financiado),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("", response_model=dict)
def listar_prestamos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    search: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar préstamos con paginación y filtros"""
    try:
        logger.info(f"Listar préstamos - Usuario: {current_user.email}")

        query = db.query(Prestamo)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Prestamo.nombres.ilike(search_pattern),
                    Prestamo.cedula.ilike(search_pattern),
                )
            )

        if estado:
            query = query.filter(Prestamo.estado == estado)

        # Paginación
        total = query.count()
        skip = (page - 1) * per_page
        prestamos = (
            query.order_by(Prestamo.fecha_registro.desc())
            .offset(skip)
            .limit(per_page)
            .all()
        )

        # Serializar préstamos usando PrestamoResponse
        prestamos_serializados = []
        for prestamo in prestamos:
            try:
                prestamo_dict = PrestamoResponse.model_validate(prestamo).model_dump()
                prestamos_serializados.append(prestamo_dict)
            except Exception as e:
                logger.error(f"Error serializando préstamo {prestamo.id}: {str(e)}")
                continue

        return {
            "data": prestamos_serializados,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error en listar_prestamos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("", response_model=PrestamoResponse)
def crear_prestamo(
    prestamo_data: PrestamoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear un nuevo préstamo"""
    try:
        logger.info(f"Crear préstamo - Usuario: {current_user.email}")

        # 1. Verificar que el cliente existe
        cliente = obtener_datos_cliente(prestamo_data.cedula, db)
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail=f"Cliente con cédula {prestamo_data.cedula} no encontrado",
            )

        # 2. Calcular número de cuotas automáticamente
        numero_cuotas, cuota_periodo = calcular_cuotas(
            prestamo_data.total_financiamiento, prestamo_data.modalidad_pago
        )

        # 3. Crear el préstamo
        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=prestamo_data.cedula,
            nombres=cliente.nombres,
            total_financiamiento=prestamo_data.total_financiamiento,
            fecha_requerimiento=prestamo_data.fecha_requerimiento,
            modalidad_pago=prestamo_data.modalidad_pago,
            numero_cuotas=numero_cuotas,
            cuota_periodo=cuota_periodo,
            tasa_interes=Decimal(0.00),  # 0% por defecto
            producto=prestamo_data.producto,
            producto_financiero=prestamo_data.producto_financiero,
            estado="DRAFT",
            usuario_proponente=current_user.email,
        )

        db.add(prestamo)
        db.commit()
        db.refresh(prestamo)

        # 4. Registrar en auditoría
        crear_registro_auditoria(
            prestamo_id=prestamo.id,
            cedula=prestamo.cedula,
            usuario=current_user.email,
            campo_modificado="PRESTAMO_CREADO",
            valor_anterior="",
            valor_nuevo=f"Préstamo creado para {prestamo.nombres}",
            accion="CREAR",
            estado_anterior=None,
            estado_nuevo="DRAFT",
            db=db,
        )

        return prestamo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en crear_prestamo: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cedula/{cedula}", response_model=list[PrestamoResponse])
def buscar_prestamos_por_cedula(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buscar préstamos por cédula del cliente"""
    prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()
    return prestamos


@router.get("/auditoria/{prestamo_id}", response_model=list[dict])
def obtener_auditoria_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de auditoría de un préstamo"""
    auditorias = (
        db.query(PrestamoAuditoria)
        .filter(PrestamoAuditoria.prestamo_id == prestamo_id)
        .order_by(PrestamoAuditoria.fecha_cambio.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "usuario": a.usuario,
            "campo_modificado": a.campo_modificado,
            "valor_anterior": a.valor_anterior,
            "valor_nuevo": a.valor_nuevo,
            "accion": a.accion,
            "estado_anterior": a.estado_anterior,
            "estado_nuevo": a.estado_nuevo,
            "observaciones": a.observaciones,
            "fecha_cambio": a.fecha_cambio.isoformat(),
        }
        for a in auditorias
    ]


@router.get("/{prestamo_id}", response_model=PrestamoResponse)
def obtener_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener un préstamo por ID"""
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    return prestamo


@router.put("/{prestamo_id}", response_model=PrestamoResponse)
def actualizar_prestamo(
    prestamo_id: int,
    prestamo_data: PrestamoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar un préstamo"""
    try:
        # 1. Buscar préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        # 2. Verificar permisos
        verificar_permisos_edicion(prestamo, current_user)

        # 3. Guardar valores antiguos para auditoría
        valores_viejos = {
            "total_financiamiento": str(prestamo.total_financiamiento),
            "modalidad_pago": prestamo.modalidad_pago,
            "estado": prestamo.estado,
        }

        # 4. Aplicar cambios simples
        aplicar_cambios_prestamo(prestamo, prestamo_data)

        # 5. Procesar cambio de estado si aplica
        if prestamo_data.estado is not None and puede_cambiar_estado(
            prestamo, prestamo_data.estado, current_user
        ):
            procesar_cambio_estado(prestamo, prestamo_data.estado, current_user, db)

        # 6. Guardar cambios
        db.commit()
        db.refresh(prestamo)

        # 7. Registrar en auditoría
        crear_registro_auditoria(
            prestamo_id=prestamo.id,
            cedula=prestamo.cedula,
            usuario=current_user.email,
            campo_modificado="ACTUALIZACION_GENERAL",
            valor_anterior=str(valores_viejos),
            valor_nuevo="Préstamo actualizado",
            accion="EDITAR",
            db=db,
        )

        return prestamo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_prestamo: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/{prestamo_id}")
def eliminar_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar un préstamo (solo Admin)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Eliminar registros de auditoría asociados
    db.query(PrestamoAuditoria).filter(
        PrestamoAuditoria.prestamo_id == prestamo_id
    ).delete()

    db.delete(prestamo)
    db.commit()

    return {"message": "Préstamo eliminado exitosamente"}


@router.post("/{prestamo_id}/generar-amortizacion")
def generar_amortizacion_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generar tabla de amortización para un préstamo aprobado (Admin y Analistas)"""
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    if prestamo.estado != "APROBADO":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden generar cuotas para préstamos aprobados",
        )

    if not prestamo.fecha_base_calculo:
        raise HTTPException(
            status_code=400, detail="El préstamo no tiene fecha base de cálculo"
        )

    try:
        cuotas_generadas = generar_amortizacion(
            prestamo, prestamo.fecha_base_calculo, db
        )

        return {
            "message": "Tabla de amortización generada exitosamente",
            "cuotas_generadas": len(cuotas_generadas),
            "prestamo_id": prestamo_id,
        }
    except Exception as e:
        logger.error(f"Error generando amortización: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generando tabla de amortización: {str(e)}"
        )


@router.get("/{prestamo_id}/cuotas", response_model=list[dict])
def obtener_cuotas_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener cuotas de un préstamo"""
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    from app.services.prestamo_amortizacion_service import obtener_cuotas_prestamo

    cuotas = obtener_cuotas_prestamo(prestamo_id, db)

    return [
        {
            "id": c.id,
            "numero_cuota": c.numero_cuota,
            "fecha_vencimiento": c.fecha_vencimiento,
            "monto_cuota": float(c.monto_cuota),
            "monto_capital": float(c.monto_capital),
            "monto_interes": float(c.monto_interes),
            "saldo_capital_inicial": float(c.saldo_capital_inicial),
            "saldo_capital_final": float(c.saldo_capital_final),
            "capital_pagado": float(c.capital_pagado),
            "interes_pagado": float(c.interes_pagado),
            "total_pagado": float(c.total_pagado),
            "capital_pendiente": float(c.capital_pendiente),
            "interes_pendiente": float(c.interes_pendiente),
            "estado": c.estado,
            "dias_mora": c.dias_mora,
            "monto_mora": float(c.monto_mora),
        }
        for c in cuotas
    ]


def actualizar_cuotas_segun_plazo_maximo(
    prestamo: Prestamo,
    plazo_maximo_meses: int,
    db: Session,
):
    """
    Recalcula y actualiza el número de cuotas según el plazo máximo
    determinado por la evaluación de riesgo.
    """
    # Recalcular cuotas con plazo máximo
    numero_cuotas, cuota_periodo = calcular_cuotas(
        prestamo.total_financiamiento, prestamo.modalidad_pago, plazo_maximo_meses
    )

    # Actualizar préstamo
    prestamo.numero_cuotas = numero_cuotas
    prestamo.cuota_periodo = cuota_periodo

    logger.info(
        f"Cuotas recalculadas para préstamo {prestamo.id}: "
        f"{numero_cuotas} cuotas de ${cuota_periodo} "
        f"(plazo_maximo={plazo_maximo_meses} meses)"
    )

    return numero_cuotas, cuota_periodo


@router.post("/{prestamo_id}/evaluar-riesgo")
def evaluar_riesgo_prestamo(
    prestamo_id: int,
    datos_evaluacion: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluar riesgo de un préstamo usando los 6 criterios de evaluación.
    Requiere datos del cliente y del préstamo.

    FASE 2: Después de la evaluación, se determina el plazo máximo
    que se usará para recalcular las cuotas.
    """
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Agregar prestamo_id a datos
    datos_evaluacion["prestamo_id"] = prestamo_id

    try:
        evaluacion = crear_evaluacion_prestamo(datos_evaluacion, db)

        # IMPORTANTE: No actualizar cuotas aquí, solo evaluar.
        # La actualización se hace al aprobar el préstamo.

        return {
            "prestamo_id": prestamo_id,
            "puntuacion_total": float(evaluacion.puntuacion_total),
            "clasificacion_riesgo": evaluacion.clasificacion_riesgo,
            "decision_final": evaluacion.decision_final,
            "tasa_interes_aplicada": float(evaluacion.tasa_interes_aplicada),
            "plazo_maximo": evaluacion.plazo_maximo,
            "enganche_minimo": float(evaluacion.enganche_minimo),
            "requisitos_adicionales": evaluacion.requisitos_adicionales,
            "detalle_criterios": {
                "ratio_endeudamiento": {
                    "puntos": float(evaluacion.ratio_endeudamiento_puntos),
                    "calculo": float(evaluacion.ratio_endeudamiento_calculo),
                },
                "ratio_cobertura": {
                    "puntos": float(evaluacion.ratio_cobertura_puntos),
                    "calculo": float(evaluacion.ratio_cobertura_calculo),
                },
                "historial_crediticio": {
                    "puntos": float(evaluacion.historial_crediticio_puntos),
                    "descripcion": evaluacion.historial_crediticio_descripcion,
                },
                "estabilidad_laboral": {
                    "puntos": float(evaluacion.estabilidad_laboral_puntos),
                    "anos_empleo": float(evaluacion.anos_empleo),
                },
                "tipo_empleo": {
                    "puntos": float(evaluacion.tipo_empleo_puntos),
                    "descripcion": evaluacion.tipo_empleo_descripcion,
                },
                "enganche_garantias": {
                    "puntos": float(evaluacion.enganche_garantias_puntos),
                    "calculo": float(evaluacion.enganche_garantias_calculo),
                },
            },
        }
    except Exception as e:
        logger.error(f"Error evaluando riesgo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluando riesgo: {str(e)}")


@router.post("/{prestamo_id}/aplicar-condiciones-aprobacion")
def aplicar_condiciones_aprobacion(
    prestamo_id: int,
    condiciones: dict,  # {plazo_maximo, tasa_interes, fecha_base_calculo, estado, observaciones}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aplica las condiciones determinadas por la evaluación de riesgo.

    FASE 2: Después de evaluar el riesgo, el admin puede aprobar el préstamo
    y aplicar las condiciones (plazo máximo recalcula cuotas, tasa de interés, etc.).

    Ejemplo de uso:
    POST /api/v1/prestamos/123/aplicar-condiciones-aprobacion
    {
        "plazo_maximo": 24,  # meses según evaluación
        "tasa_interes": 12.0,
        "fecha_base_calculo": "2025-11-01",
        "estado": "APROBADO",
        "observaciones": "Aprobado con condiciones de alto riesgo"
    }
    """
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Solo admin puede aplicar condiciones
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden aprobar con condiciones",
        )

    try:
        from datetime import datetime
        from dateutil import parser as date_parser

        # Guardar valores anteriores para auditoría
        valores_anterior = {
            "numero_cuotas": prestamo.numero_cuotas,
            "cuota_periodo": str(prestamo.cuota_periodo),
            "tasa_interes": str(prestamo.tasa_interes),
            "estado": prestamo.estado,
        }

        # Aplicar plazo máximo y recalcular cuotas (SI VIENE)
        if "plazo_maximo" in condiciones:
            actualizar_cuotas_segun_plazo_maximo(
                prestamo, condiciones["plazo_maximo"], db
            )

        # Aplicar tasa de interés (SI VIENE)
        if "tasa_interes" in condiciones:
            prestamo.tasa_interes = Decimal(str(condiciones["tasa_interes"]))

        # Aplicar fecha base de cálculo (SI VIENE)
        if "fecha_base_calculo" in condiciones:
            fecha_str = condiciones["fecha_base_calculo"]
            prestamo.fecha_base_calculo = date_parser.parse(fecha_str).date()

        # Aplicar observaciones
        if "observaciones" in condiciones:
            prestamo.observaciones = condiciones["observaciones"]

        # Cambiar estado si se especifica
        nuevo_estado = condiciones.get("estado")
        if nuevo_estado:
            procesar_cambio_estado(
                prestamo,
                nuevo_estado,
                current_user,
                db,
                plazo_maximo_meses=condiciones.get("plazo_maximo"),
                tasa_interes=(
                    Decimal(str(condiciones.get("tasa_interes", 0)))
                    if "tasa_interes" in condiciones
                    else None
                ),
                fecha_base_calculo=prestamo.fecha_base_calculo,
            )

        db.commit()
        db.refresh(prestamo)

        # Registrar en auditoría
        crear_registro_auditoria(
            prestamo_id=prestamo.id,
            cedula=prestamo.cedula,
            usuario=current_user.email,
            campo_modificado="CONDICIONES_APLICADAS",
            valor_anterior=str(valores_anterior),
            valor_nuevo=str(condiciones),
            accion="APLICAR_CONDICIONES",
            estado_anterior=prestamo.estado,
            estado_nuevo=nuevo_estado or prestamo.estado,
            db=db,
        )

        return {
            "message": "Condiciones aplicadas exitosamente",
            "prestamo_id": prestamo_id,
            "numero_cuotas_actualizado": prestamo.numero_cuotas,
            "cuota_periodo_actualizado": float(prestamo.cuota_periodo),
            "tasa_interes": float(prestamo.tasa_interes),
            "estado": prestamo.estado,
        }

    except Exception as e:
        logger.error(f"Error aplicando condiciones: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error aplicando condiciones: {str(e)}"
        )
