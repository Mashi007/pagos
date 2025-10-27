import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
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
def calcular_cuotas(total: Decimal, modalidad: str) -> tuple[int, Decimal]:
    """
    Calcula automáticamente el número de cuotas según la modalidad de pago.

    TABLA 12: AJUSTE DE FRECUENCIA DE PAGO
    - MENSUAL: 36 cuotas
    - QUINCENAL: 72 cuotas (36 * 2)
    - SEMANAL: 144 cuotas (36 * 4)
    """
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


def actualizar_monto_y_cuotas(prestamo: Prestamo, monto: Decimal):
    """Actualiza monto y recalcula cuotas"""
    prestamo.total_financiamiento = monto
    prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(
        prestamo.total_financiamiento, prestamo.modalidad_pago
    )


def procesar_cambio_estado(
    prestamo: Prestamo, nuevo_estado: str, current_user: User, db: Session
):
    """Procesa el cambio de estado del préstamo"""
    from datetime import datetime

    estado_anterior = prestamo.estado
    prestamo.estado = nuevo_estado

    if nuevo_estado == "APROBADO":
        prestamo.usuario_aprobador = current_user.email
        prestamo.fecha_aprobacion = datetime.now()

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

        return {
            "data": prestamos,
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
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        # Verificar estado: si está APROBADO/RECHAZADO, solo Admin puede editar
        if prestamo.estado in ["APROBADO", "RECHAZADO"]:
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail="Solo administradores pueden editar préstamos aprobados/rechazados",
                )

        # Guardar valores antiguos para auditoría
        valores_viejos = {
            "total_financiamiento": str(prestamo.total_financiamiento),
            "modalidad_pago": prestamo.modalidad_pago,
            "estado": prestamo.estado,
        }

        # Actualizar campos
        if prestamo_data.total_financiamiento is not None:
            actualizar_monto_y_cuotas(prestamo, prestamo_data.total_financiamiento)

        if prestamo_data.modalidad_pago is not None:
            prestamo.modalidad_pago = prestamo_data.modalidad_pago
            prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(
                prestamo.total_financiamiento, prestamo.modalidad_pago
            )

        if prestamo_data.estado is not None:
            if current_user.is_superuser or (
                prestamo.estado == "DRAFT" and prestamo_data.estado == "EN_REVISION"
            ):
                procesar_cambio_estado(prestamo, prestamo_data.estado, current_user, db)

        if prestamo_data.observaciones is not None:
            prestamo.observaciones = prestamo_data.observaciones

        db.commit()
        db.refresh(prestamo)

        # Registrar en auditoría (simplificado)
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
    if not current_user.is_superuser:
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


@router.post("/{prestamo_id}/generar-amortizacion")
def generar_amortizacion_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generar tabla de amortización para un préstamo aprobado (solo Admin)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Solo administradores")

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
    """
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Agregar prestamo_id a datos
    datos_evaluacion["prestamo_id"] = prestamo_id
    
    try:
        evaluacion = crear_evaluacion_prestamo(datos_evaluacion, db)
        
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
