"""
Endpoints para el módulo de Préstamos
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.prestamo import Prestamo
from app.models.prestamo_auditoria import PrestamoAuditoria
from app.models.user import User
from app.schemas.prestamo import (
    PrestamoCreate,
    PrestamoResponse,
    PrestamoUpdate,
)
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion as generar_amortizacion
from app.services.prestamo_amortizacion_service import obtener_cuotas_prestamo as obtener_cuotas_service
from app.services.prestamo_evaluacion_service import crear_evaluacion_prestamo

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# FUNCIONES AUXILIARES
# ============================================
def calcular_cuotas(total: Decimal, modalidad: str, plazo_maximo_meses: Optional[int] = None) -> tuple[int, Decimal]:
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
    """Obtiene los datos del cliente por cédula (normalizando mayúsculas/espacios)"""
    if not cedula:
        return None
    ced_norm = str(cedula).strip().upper()
    return db.query(Cliente).filter(Cliente.cedula == ced_norm).first()


def verificar_permisos_edicion(prestamo: Prestamo, current_user: User):
    """Verifica si el usuario tiene permisos para editar el préstamo"""
    if prestamo.estado in ["APROBADO", "RECHAZADO"]:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden editar préstamos aprobados/rechazados",
            )


def puede_cambiar_estado(prestamo: Prestamo, nuevo_estado: str, current_user: User) -> bool:
    """Verifica si el usuario puede cambiar el estado del préstamo"""
    return current_user.is_admin or (prestamo.estado == "DRAFT" and nuevo_estado == "EN_REVISION")


def aplicar_cambios_prestamo(prestamo: Prestamo, prestamo_data: PrestamoUpdate):
    """Aplica los cambios del prestamo_data al prestamo"""
    if prestamo_data.total_financiamiento is not None:
        actualizar_monto_y_cuotas(prestamo, prestamo_data.total_financiamiento)

    if prestamo_data.modalidad_pago is not None:
        prestamo.modalidad_pago = prestamo_data.modalidad_pago
        prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(
            prestamo.total_financiamiento, prestamo.modalidad_pago
        )

    # Aplicar cambios directos de numero_cuotas y cuota_periodo si se proporcionan
    if prestamo_data.numero_cuotas is not None:
        prestamo.numero_cuotas = prestamo_data.numero_cuotas

    if prestamo_data.cuota_periodo is not None:
        prestamo.cuota_periodo = prestamo_data.cuota_periodo

    if prestamo_data.tasa_interes is not None:
        prestamo.tasa_interes = prestamo_data.tasa_interes

    if prestamo_data.fecha_base_calculo is not None:
        prestamo.fecha_base_calculo = prestamo_data.fecha_base_calculo

    if prestamo_data.fecha_requerimiento is not None:
        prestamo.fecha_requerimiento = prestamo_data.fecha_requerimiento

    if prestamo_data.observaciones is not None:
        prestamo.observaciones = prestamo_data.observaciones


def actualizar_monto_y_cuotas(prestamo: Prestamo, monto: Decimal):
    """Actualiza monto y recalcula cuotas"""
    prestamo.total_financiamiento = monto
    prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(prestamo.total_financiamiento, prestamo.modalidad_pago)


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
    estado_anterior = prestamo.estado
    prestamo.estado = nuevo_estado

    if nuevo_estado == "APROBADO":
        prestamo.usuario_aprobador = current_user.email
        prestamo.fecha_aprobacion = datetime.now()

        # Aplicar condiciones desde evaluación de riesgo (FASE 2)
        if plazo_maximo_meses:
            numero_cuotas, cuota_periodo = actualizar_cuotas_segun_plazo_maximo(prestamo, plazo_maximo_meses, db)
            logger.info(f"Cuotas ajustadas según análisis de riesgo: {numero_cuotas} cuotas")

        # Aplicar tasa de interés desde evaluación
        if tasa_interes:
            prestamo.tasa_interes = tasa_interes

        # Aplicar fecha base de cálculo
        if fecha_base_calculo:
            prestamo.fecha_base_calculo = fecha_base_calculo

        # Si se aprueba y tiene fecha_base_calculo, generar tabla de amortización
        if prestamo.fecha_base_calculo:
            try:
                # Convertir a date si es necesario
                if isinstance(prestamo.fecha_base_calculo, str):
                    fecha = date_parse(prestamo.fecha_base_calculo).date()
                else:
                    fecha = prestamo.fecha_base_calculo

                generar_amortizacion(prestamo, fecha, db)
                logger.info(f"Tabla de amortización generada para préstamo {prestamo.id} con fecha de desembolso: {fecha}")
            except Exception as e:
                logger.error(f"Error generando amortización: {str(e)}")
                # No fallar el préstamo si falla la generación de cuotas

        # MÓDULO APROBACIONES DESHABILITADO - Registro automático comentado
        # try:
        #     aprobacion = Aprobacion(
        #         solicitante_id=current_user.id,
        #         revisor_id=current_user.id,
        #         tipo_solicitud="PRESTAMO",
        #         entidad="Cliente",
        #         entidad_id=prestamo.cliente_id,
        #         justificacion=f"Préstamo aprobado para {prestamo.nombres} (Cédula: {prestamo.cedula}). Monto: ${prestamo.total_financiamiento}, Cuotas: {prestamo.numero_cuotas}",
        #         estado="APROBADA",
        #         resultado=f"Préstamo #{prestamo.id} aprobado por {current_user.email}",
        #         fecha_aprobacion=datetime.now(),
        #         prioridad="NORMAL",
        #     )
        #     db.add(aprobacion)
        #     db.commit()
        #     logger.info(f"Registro de aprobación creado para préstamo {prestamo.id}")
        # except Exception as e:
        #     logger.warning(
        #         f"Error creando registro de aprobación (no crítico): {str(e)}"
        #     )

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


def serializar_prestamo(prestamo: Prestamo) -> dict:
    """Serializa un préstamo de forma segura, manejando campos que pueden no existir en BD"""
    return {
        "id": prestamo.id,
        "cliente_id": prestamo.cliente_id,
        "cedula": prestamo.cedula,
        "nombres": prestamo.nombres,
        "total_financiamiento": prestamo.total_financiamiento,
        "fecha_requerimiento": prestamo.fecha_requerimiento,
        "modalidad_pago": prestamo.modalidad_pago,
        "numero_cuotas": prestamo.numero_cuotas,
        "cuota_periodo": prestamo.cuota_periodo,
        "tasa_interes": prestamo.tasa_interes,
        "fecha_base_calculo": prestamo.fecha_base_calculo,
        "producto": prestamo.producto,
        "producto_financiero": prestamo.producto_financiero,
        "concesionario": getattr(prestamo, "concesionario", None),
        "analista": getattr(prestamo, "analista", None),
        "modelo_vehiculo": getattr(prestamo, "modelo_vehiculo", None),
        "estado": prestamo.estado,
        "usuario_proponente": prestamo.usuario_proponente,
        "usuario_aprobador": prestamo.usuario_aprobador,
        "usuario_autoriza": getattr(prestamo, "usuario_autoriza", None),
        "observaciones": prestamo.observaciones,
        "fecha_registro": prestamo.fecha_registro,
        "fecha_aprobacion": prestamo.fecha_aprobacion,
        "fecha_actualizacion": prestamo.fecha_actualizacion,
    }


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
        prestamos_por_estado = db.query(Prestamo.estado, db.func.count(Prestamo.id)).group_by(Prestamo.estado).all()

        total_financiado = db.query(db.func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0.00")

        return {
            "total_prestamos": total_prestamos,
            "prestamos_por_estado": {estado: count for estado, count in prestamos_por_estado},
            "total_financiado": float(total_financiado),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


def _obtener_query_base_prestamos(db: Session):
    """Obtiene la query base para préstamos con columnas seguras"""
    return db.query(
        Prestamo.id,
        Prestamo.cliente_id,
        Prestamo.cedula,
        Prestamo.nombres,
        Prestamo.total_financiamiento,
        Prestamo.fecha_requerimiento,
        Prestamo.modalidad_pago,
        Prestamo.numero_cuotas,
        Prestamo.cuota_periodo,
        Prestamo.tasa_interes,
        Prestamo.fecha_base_calculo,
        Prestamo.producto,
        Prestamo.producto_financiero,
        Prestamo.estado,
        Prestamo.usuario_proponente,
        Prestamo.usuario_aprobador,
        Prestamo.observaciones,
        Prestamo.fecha_registro,
        Prestamo.fecha_aprobacion,
        Prestamo.fecha_actualizacion,
    )


def _aplicar_filtros_prestamos(
    query,
    search: Optional[str],
    estado: Optional[str],
    cedula: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
):
    """Aplica filtros a la query de préstamos"""
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

    if cedula:
        cedula_normalizada = cedula.strip().upper()
        query = query.filter(Prestamo.cedula == cedula_normalizada)

    if analista:
        query = query.filter(Prestamo.analista == analista)

    if concesionario:
        query = query.filter(Prestamo.concesionario == concesionario)

    if modelo:
        query = query.filter(Prestamo.modelo_vehiculo == modelo)

    if fecha_inicio:
        query = query.filter(Prestamo.fecha_registro >= fecha_inicio)

    if fecha_fin:
        fecha_fin_completa = datetime.combine(fecha_fin, datetime.max.time())
        query = query.filter(Prestamo.fecha_registro <= fecha_fin_completa)

    return query


def _contar_prestamos_con_manejo_error(query, db: Session) -> int:
    """Cuenta el total de préstamos con manejo de errores"""
    try:
        return query.count()
    except Exception as e:
        logger.error(f"Error contando préstamos: {str(e)}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def _obtener_prestamos_con_manejo_error(query, skip: int, per_page: int, db: Session):
    """Obtiene préstamos con paginación y manejo de errores"""
    try:
        return query.order_by(Prestamo.fecha_registro.desc()).offset(skip).limit(per_page).all()
    except Exception as e:
        logger.error(f"Error obteniendo préstamos: {str(e)}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return []


def _serializar_prestamo(row) -> Optional[dict]:
    """Serializa un préstamo de forma segura. Returns None si falla"""
    try:
        prestamo_data = {
            "id": row.id,
            "cliente_id": row.cliente_id,
            "cedula": row.cedula,
            "nombres": row.nombres,
            "total_financiamiento": row.total_financiamiento,
            "fecha_requerimiento": row.fecha_requerimiento,
            "modalidad_pago": row.modalidad_pago,
            "numero_cuotas": row.numero_cuotas,
            "cuota_periodo": row.cuota_periodo,
            "tasa_interes": row.tasa_interes,
            "fecha_base_calculo": row.fecha_base_calculo,
            "producto": row.producto,
            "producto_financiero": row.producto_financiero,
            "concesionario": None,
            "analista": None,
            "modelo_vehiculo": None,
            "estado": row.estado,
            "usuario_proponente": row.usuario_proponente,
            "usuario_aprobador": row.usuario_aprobador,
            "usuario_autoriza": None,
            "observaciones": row.observaciones,
            "fecha_registro": row.fecha_registro,
            "fecha_aprobacion": row.fecha_aprobacion,
            "fecha_actualizacion": row.fecha_actualizacion,
        }
        return PrestamoResponse.model_validate(prestamo_data).model_dump()
    except Exception as e:
        logger.error(f"Error serializando préstamo en listar: {str(e)}", exc_info=True)
        return None


def listar_prestamos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    search: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    cedula: Optional[str] = Query(None, description="Filtrar por cédula"),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo de vehículo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (fecha_registro)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin (fecha_registro)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar préstamos con paginación y filtros"""
    try:
        logger.info(f"Listar préstamos - Usuario: {current_user.email}")

        query = _obtener_query_base_prestamos(db)
        query = _aplicar_filtros_prestamos(query, search, estado, cedula, analista, concesionario, modelo, fecha_inicio, fecha_fin)

        total = _contar_prestamos_con_manejo_error(query, db)
        skip = (page - 1) * per_page
        prestamos = _obtener_prestamos_con_manejo_error(query, skip, per_page, db)

        prestamos_serializados = []
        for row in prestamos:
            prestamo_dict = _serializar_prestamo(row)
            if prestamo_dict:
                prestamos_serializados.append(prestamo_dict)

        if prestamos and not prestamos_serializados:
            logger.error(
                f"No se pudo serializar ninguno de los {len(prestamos)} préstamos. "
                "Posible problema de esquema de base de datos."
            )

        return {
            "data": prestamos_serializados,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error en listar_prestamos: {error_msg}", exc_info=True)

        if "column" in error_msg.lower() and ("does not exist" in error_msg.lower() or "no such column" in error_msg.lower()):
            detail_msg = f"Error de esquema de base de datos. " f"Es posible que falten migraciones. " f"Error: {error_msg}"
            logger.error(detail_msg)
            raise HTTPException(status_code=500, detail=detail_msg)

        raise HTTPException(status_code=500, detail=f"Error interno: {error_msg}")


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
        # Normalizar cédula (mayúsculas/sin espacios) para buscar y guardar
        cedula_norm = (prestamo_data.cedula or "").strip().upper()
        cliente = obtener_datos_cliente(cedula_norm, db)
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail=f"Cliente con cédula {prestamo_data.cedula} no encontrado",
            )

        # 2. Validar modelo de vehículo si viene y debe tener precio configurado
        if getattr(prestamo_data, "modelo_vehiculo", None):
            existente = (
                db.query(ModeloVehiculo)
                .filter(
                    ModeloVehiculo.modelo == prestamo_data.modelo_vehiculo,
                    ModeloVehiculo.activo.is_(True),
                    ModeloVehiculo.precio.isnot(None),
                )
                .first()
            )
            if not existente:
                raise HTTPException(
                    status_code=400,
                    detail="El modelo seleccionado no existe, está inactivo o no tiene precio configurado",
                )

        # 3. Determinar número de cuotas y cuota por período
        # Si el frontend envía numero_cuotas y cuota_periodo, usarlos
        # Si no, calcularlos automáticamente según modalidad
        if prestamo_data.numero_cuotas is not None and prestamo_data.cuota_periodo is not None:
            # Usar los valores enviados desde el frontend
            numero_cuotas = prestamo_data.numero_cuotas
            cuota_periodo = prestamo_data.cuota_periodo
            logger.info(f"Usando valores enviados: {numero_cuotas} cuotas, ${cuota_periodo} por período")
        else:
            # Calcular automáticamente según modalidad
            numero_cuotas, cuota_periodo = calcular_cuotas(prestamo_data.total_financiamiento, prestamo_data.modalidad_pago)
            logger.info(f"Calculados automáticamente: {numero_cuotas} cuotas, ${cuota_periodo} por período")

        # 4. Crear el préstamo
        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=cedula_norm,
            nombres=cliente.nombres,
            total_financiamiento=prestamo_data.total_financiamiento,
            fecha_requerimiento=prestamo_data.fecha_requerimiento,
            modalidad_pago=prestamo_data.modalidad_pago,
            numero_cuotas=numero_cuotas,
            cuota_periodo=cuota_periodo,
            tasa_interes=Decimal(0.00),  # 0% por defecto
            producto=prestamo_data.producto,
            producto_financiero=prestamo_data.producto_financiero,
            concesionario=prestamo_data.concesionario,
            analista=prestamo_data.analista,
            modelo_vehiculo=prestamo_data.modelo_vehiculo,
            estado="DRAFT",
            usuario_proponente=current_user.email,
            usuario_autoriza=prestamo_data.usuario_autoriza,
            observaciones=prestamo_data.observaciones,
        )

        db.add(prestamo)
        db.commit()
        db.refresh(prestamo)

        # 5. Registrar en auditoría
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

        # Serializar de forma segura antes de retornar
        prestamo_data = serializar_prestamo(prestamo)
        return PrestamoResponse.model_validate(prestamo_data)

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
    # Evitar seleccionar columnas nuevas que aún no existen en algunas BD
    prestamos = (
        db.query(
            Prestamo.id,
            Prestamo.producto,
            Prestamo.total_financiamiento,
            Prestamo.estado,
            Prestamo.fecha_registro,
        )
        .filter(Prestamo.cedula == cedula)
        .all()
    )
    # Serializar de forma segura
    return [PrestamoResponse.model_validate(serializar_prestamo(p)) for p in prestamos]


@router.get("/cedula/{cedula}/resumen", response_model=dict)
def obtener_resumen_prestamos_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener resumen de préstamos del cliente: saldo, cuotas en mora, etc."""
    from app.models.amortizacion import Cuota

    prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()

    if not prestamos:
        return {"tiene_prestamos": False, "total_prestamos": 0, "prestamos": []}

    resumen_prestamos = []
    total_saldo = Decimal("0.00")
    total_cuotas_mora = 0

    for row in prestamos:
        # Obtener cuotas del préstamo
        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == row.id).all()

        # Calcular saldo pendiente (suma de capital_pendiente + interes_pendiente + monto_mora)
        saldo_pendiente = Decimal("0.00")
        cuotas_en_mora = 0

        for cuota in cuotas:
            saldo_pendiente += cuota.capital_pendiente + cuota.interes_pendiente + cuota.monto_mora

            # Contar cuotas en mora (vencidas y no pagadas)
            if cuota.fecha_vencimiento < date.today() and cuota.estado != "PAGADO":
                cuotas_en_mora += 1

        total_saldo += saldo_pendiente
        total_cuotas_mora += cuotas_en_mora

        resumen_prestamos.append(
            {
                "id": row.id,
                # Usar producto como respaldo. Evitamos consultar modelo_vehiculo
                # ya que puede no existir físicamente en la tabla todavía.
                "modelo_vehiculo": row.producto,
                "total_financiamiento": float(row.total_financiamiento),
                "saldo_pendiente": float(saldo_pendiente),
                "cuotas_en_mora": cuotas_en_mora,
                "estado": row.estado,
                "fecha_registro": (row.fecha_registro.isoformat() if row.fecha_registro else None),
            }
        )

    return {
        "tiene_prestamos": True,
        "total_prestamos": len(resumen_prestamos),
        "total_saldo_pendiente": float(total_saldo),
        "total_cuotas_mora": total_cuotas_mora,
        "prestamos": resumen_prestamos,
    }


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

    # Serializar de forma segura
    prestamo_data = serializar_prestamo(prestamo)
    return PrestamoResponse.model_validate(prestamo_data)


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
        if prestamo_data.estado is not None and puede_cambiar_estado(prestamo, prestamo_data.estado, current_user):
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

        # Serializar de forma segura antes de retornar
        prestamo_data = serializar_prestamo(prestamo)
        return PrestamoResponse.model_validate(prestamo_data)

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
    db.query(PrestamoAuditoria).filter(PrestamoAuditoria.prestamo_id == prestamo_id).delete()

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
        raise HTTPException(status_code=400, detail="El préstamo no tiene fecha base de cálculo")

    try:
        cuotas_generadas = generar_amortizacion(prestamo, prestamo.fecha_base_calculo, db)

        return {
            "message": "Tabla de amortización generada exitosamente",
            "cuotas_generadas": len(cuotas_generadas),
            "prestamo_id": prestamo_id,
        }
    except Exception as e:
        logger.error(f"Error generando amortización: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando tabla de amortización: {str(e)}")


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

    cuotas = obtener_cuotas_service(prestamo_id, db)

    resultado = []
    estados_encontrados = []

    for c in cuotas:
        # Determinar estado real basado en total_pagado y monto_cuota
        estado_real = c.estado
        if c.total_pagado >= c.monto_cuota:
            # Si está completamente pagado pero el estado no es PAGADO, corregirlo
            if c.estado != "PAGADO":
                logger.warning(
                    f"⚠️ [obtener_cuotas_prestamo] Préstamo {prestamo_id}, Cuota {c.numero_cuota}: "
                    f"Inconsistencia detectada - total_pagado ({c.total_pagado}) >= monto_cuota ({c.monto_cuota}) "
                    f"pero estado BD es '{c.estado}'"
                )
                estado_real = "PAGADO"
        elif c.total_pagado > 0 and c.fecha_vencimiento < date.today():
            # Tiene pago parcial y está vencida
            if c.estado not in ["ATRASADO", "PARCIAL"]:
                logger.warning(
                    f"⚠️ [obtener_cuotas_prestamo] Préstamo {prestamo_id}, Cuota {c.numero_cuota}: "
                    f"Tiene pago parcial ({c.total_pagado}) y está vencida pero estado es '{c.estado}'"
                )
                estado_real = "ATRASADO"

        cuota_dict = {
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
            "estado": estado_real,  # Usar estado corregido si hay inconsistencia
            "dias_mora": c.dias_mora,
            "monto_mora": float(c.monto_mora),
        }
        resultado.append(cuota_dict)
        estados_encontrados.append(f"{c.numero_cuota}:{estado_real}(BD:{c.estado})")

    # 🔍 LOG: Verificar estados devueltos
    logger.info(
        f"📊 [obtener_cuotas_prestamo] Préstamo {prestamo_id}: "
        f"{len(resultado)} cuotas. Estados: {estados_encontrados[:10]}"
    )

    return resultado


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
    numero_cuotas, cuota_periodo = calcular_cuotas(prestamo.total_financiamiento, prestamo.modalidad_pago, plazo_maximo_meses)

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
    Evaluar riesgo de un préstamo usando los 7 criterios de evaluación (100 puntos).
    Requiere datos del cliente y del préstamo.

    Sistema de 100 puntos:
    - Criterio 1: Capacidad de Pago (29 pts) - 14 pts Endeudamiento + 15 pts Cobertura
    - Criterio 2: Estabilidad Laboral (23 pts) - 9 pts Antigüedad + 8 pts Tipo Empleo + 6 pts Sector
    - Criterio 3: Referencias Personales (9 pts) - 3 referencias × 3 pts c/u
    - Criterio 4: Arraigo Geográfico (7 pts) - 4 pts Familiar + 3 pts Laboral
    - Criterio 5: Perfil Sociodemográfico (17 pts) - 6 pts Vivienda + 6 pts Estado Civil + 5 pts Hijos
    - Criterio 6: Edad del Cliente (10 pts)
    - Criterio 7: Capacidad de Maniobra (5 pts)

    FASE 2: Después de la evaluación, se determina el plazo máximo
    que se usará para recalcular las cuotas.
    """
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Agregar prestamo_id y cuota_mensual del préstamo desde BD
    datos_evaluacion["prestamo_id"] = prestamo_id

    # IMPORTANTE: Tomar la cuota del préstamo desde la base de datos
    if "cuota_mensual" not in datos_evaluacion or not datos_evaluacion["cuota_mensual"]:
        datos_evaluacion["cuota_mensual"] = float(prestamo.cuota_periodo) if prestamo.cuota_periodo else 0

    # AGREGAR: Obtener edad del cliente desde la base de datos en años y meses
    if "edad" not in datos_evaluacion or not datos_evaluacion["edad"]:
        # Buscar cliente por cédula
        cliente = db.query(Cliente).filter(Cliente.cedula == prestamo.cedula).first()
        if cliente and cliente.fecha_nacimiento:
            # Calcular edad exacta en años con meses desde fecha de nacimiento
            hoy = date.today()
            nacimiento = cliente.fecha_nacimiento

            # Calcular años
            años = hoy.year - nacimiento.year

            # Calcular meses
            if hoy.month < nacimiento.month or (hoy.month == nacimiento.month and hoy.day < nacimiento.day):
                años -= 1

            # Calcular meses adicionales
            if hoy.month >= nacimiento.month:
                meses = hoy.month - nacimiento.month
                if hoy.day < nacimiento.day:
                    meses -= 1
            else:
                meses = (12 - nacimiento.month) + hoy.month
                if hoy.day < nacimiento.day:
                    meses -= 1

            # Normalizar meses (si >= 12, agregar al año)
            if meses >= 12:
                años += meses // 12
                meses = meses % 12

            # Edad total en años decimales para el cálculo
            edad_total = años + (meses / 12)
            datos_evaluacion["edad"] = edad_total
            datos_evaluacion["edad_años"] = años
            datos_evaluacion["edad_meses"] = meses

            logger.info(
                f"Edad calculada desde BD: {años} años y {meses} meses " f"(fecha_nacimiento: {cliente.fecha_nacimiento})"
            )
        else:
            datos_evaluacion["edad"] = 25.0  # Valor por defecto si no se encuentra
            datos_evaluacion["edad_años"] = 25
            datos_evaluacion["edad_meses"] = 0
            logger.warning(f"No se encontró fecha de nacimiento para cédula {prestamo.cedula}, usando valor por defecto")

    # Log para debugging
    logger.info(
        f"Evaluando préstamo {prestamo_id} con cuota: {datos_evaluacion['cuota_mensual']} USD, edad: {datos_evaluacion.get('edad', 'N/A')} años"
    )

    try:
        evaluacion = crear_evaluacion_prestamo(datos_evaluacion, db)

        # IMPORTANTE: Cambiar estado a EVALUADO después de completar la evaluación
        # Esto permite que aparezca el icono de "Aprobar Crédito" en el dashboard
        if prestamo.estado in ["DRAFT", "EN_REVISION"]:
            prestamo.estado = "EVALUADO"
            db.commit()
            logger.info(f"Préstamo {prestamo_id} cambiado a estado EVALUADO después de evaluación de riesgo")

        # IMPORTANTE: La evaluación solo genera SUGERENCIAS
        # El humano (admin) debe decidir si aprobar o rechazar
        # NO se aprueba automáticamente, solo se marca como candidato para aprobación
        if evaluacion.decision_final == "APROBADO_AUTOMATICO":
            logger.info(
                f"Préstamo {prestamo_id} es candidato para aprobación "
                f"(Riesgo: {evaluacion.clasificacion_riesgo}, Puntuación: {evaluacion.puntuacion_total}/100)"
            )
            logger.info(
                "⚠️ El sistema SUGIERE aprobar, pero requiere decisión humana. "
                "Usar endpoint '/aplicar-condiciones-aprobacion' para aprobar manualmente."
            )

        return {
            "prestamo_id": prestamo_id,
            "puntuacion_total": float(evaluacion.puntuacion_total or 0),
            "clasificacion_riesgo": evaluacion.clasificacion_riesgo,
            "decision_final": evaluacion.decision_final,
            "requiere_aprobacion_manual": evaluacion.decision_final == "APROBADO_AUTOMATICO",
            "mensaje": (
                "✅ Préstamo candidato para aprobación. Debe ser aprobado manualmente con tasa sugerida."
                if evaluacion.decision_final == "APROBADO_AUTOMATICO"
                else "⚠️ Revisar antes de aprobar"
            ),
            "sugerencias": {
                "tasa_interes_sugerida": float(evaluacion.tasa_interes_aplicada or 0),
                "plazo_maximo_sugerido": evaluacion.plazo_maximo,
                "enganche_minimo_sugerido": float(evaluacion.enganche_minimo or 0),
                "requisitos_adicionales": evaluacion.requisitos_adicionales,
            },
            "tasa_interes_aplicada": float(evaluacion.tasa_interes_aplicada or 0),
            "plazo_maximo": evaluacion.plazo_maximo,
            "enganche_minimo": float(evaluacion.enganche_minimo or 0),
            "requisitos_adicionales": evaluacion.requisitos_adicionales,
            "detalle_criterios": {
                # Criterio 1: Capacidad de Pago (29 puntos)
                "ratio_endeudamiento": {
                    "puntos": float(evaluacion.ratio_endeudamiento_puntos or 0),
                    "calculo": float(evaluacion.ratio_endeudamiento_calculo or 0),
                },
                "ratio_cobertura": {
                    "puntos": float(evaluacion.ratio_cobertura_puntos or 0),
                    "calculo": float(evaluacion.ratio_cobertura_calculo or 0),
                },
                # Criterio 2: Estabilidad Laboral (23 puntos)
                "antiguedad_trabajo": {
                    "puntos": float(evaluacion.antiguedad_trabajo_puntos or 0),
                    "meses": (float(evaluacion.meses_trabajo) if evaluacion.meses_trabajo else 0),
                },
                "tipo_empleo": {
                    "puntos": float(evaluacion.tipo_empleo_puntos or 0),
                    "descripcion": evaluacion.tipo_empleo_descripcion,
                },
                "sector_economico": {
                    "puntos": float(evaluacion.sector_economico_puntos or 0),
                    "descripcion": evaluacion.sector_economico_descripcion,
                },
                # Criterio 3: Referencias (9 puntos)
                "referencias": {
                    "puntos": float(evaluacion.referencias_puntos or 0),
                    "descripcion": evaluacion.referencias_descripcion,
                    "referencia1_calificacion": evaluacion.referencia1_calificacion,
                    "referencia1_observaciones": evaluacion.referencia1_observaciones,
                    "referencia2_calificacion": evaluacion.referencia2_calificacion,
                    "referencia2_observaciones": evaluacion.referencia2_observaciones,
                    "referencia3_calificacion": evaluacion.referencia3_calificacion,
                    "referencia3_observaciones": evaluacion.referencia3_observaciones,
                },
                # Criterio 4: Arraigo Geográfico (7 puntos)
                "arraigo_vivienda": float(evaluacion.arraigo_vivienda_puntos or 0),
                "arraigo_familiar": float(evaluacion.arraigo_familiar_puntos or 0),
                "arraigo_laboral": float(evaluacion.arraigo_laboral_puntos or 0),
                # Criterio 5: Perfil Sociodemográfico (17 puntos)
                "vivienda": {
                    "puntos": float(evaluacion.vivienda_puntos or 0),
                    "descripcion": evaluacion.vivienda_descripcion,
                },
                "estado_civil": {
                    "puntos": float(evaluacion.estado_civil_puntos or 0),
                    "descripcion": evaluacion.estado_civil_descripcion,
                },
                "hijos": {
                    "puntos": float(evaluacion.hijos_puntos or 0),
                    "descripcion": evaluacion.hijos_descripcion,
                },
                # Criterio 6: Edad (10 puntos)
                "edad": {
                    "puntos": float(evaluacion.edad_puntos or 0),
                    "cliente": evaluacion.edad_cliente,
                },
                # Criterio 7: Capacidad de Maniobra (5 puntos)
                "capacidad_maniobra": {
                    "puntos": float(evaluacion.enganche_garantias_puntos or 0),
                    "porcentaje_residual": float(evaluacion.enganche_garantias_calculo or 0),
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
        # Guardar valores anteriores para auditoría
        valores_anterior = {
            "numero_cuotas": prestamo.numero_cuotas,
            "cuota_periodo": str(prestamo.cuota_periodo),
            "tasa_interes": str(prestamo.tasa_interes),
            "estado": prestamo.estado,
        }

        # Aplicar plazo máximo y recalcular cuotas (SI VIENE)
        if "plazo_maximo" in condiciones:
            actualizar_cuotas_segun_plazo_maximo(prestamo, condiciones["plazo_maximo"], db)

        # Aplicar tasa de interés (SI VIENE)
        if "tasa_interes" in condiciones:
            prestamo.tasa_interes = Decimal(str(condiciones["tasa_interes"]))

        # Aplicar fecha base de cálculo (SI VIENE)
        if "fecha_base_calculo" in condiciones:
            fecha_str = condiciones["fecha_base_calculo"]
            prestamo.fecha_base_calculo = date_parse(fecha_str).date()

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
                tasa_interes=(Decimal(str(condiciones.get("tasa_interes", 0))) if "tasa_interes" in condiciones else None),
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
        raise HTTPException(status_code=500, detail=f"Error aplicando condiciones: {str(e)}")
