"""
Endpoints para el módulo de Préstamos
"""

import logging
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from dateutil.parser import parse as date_parse  # type: ignore[import-untyped]
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Path, Query  # type: ignore[import-untyped]
from sqlalchemy import and_, case, func, or_  # type: ignore[import-untyped]
from sqlalchemy.exc import OperationalError, ProgrammingError  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.modelo_riesgo import ModeloRiesgo
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
    """Obtiene los datos del cliente por cédula (normalizando mayúsculas/espacios)
    IMPORTANTE: Solo retorna clientes con estado = 'ACTIVO' para permitir crear préstamos"""
    if not cedula:
        return None
    ced_norm = str(cedula).strip().upper()
    return db.query(Cliente).filter(Cliente.cedula == ced_norm, Cliente.estado == "ACTIVO").first()


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
    if prestamo_data.valor_activo is not None:
        prestamo.valor_activo = prestamo_data.valor_activo  # type: ignore[assignment]

    if prestamo_data.total_financiamiento is not None:
        actualizar_monto_y_cuotas(prestamo, prestamo_data.total_financiamiento)

    if prestamo_data.modalidad_pago is not None:
        prestamo.modalidad_pago = prestamo_data.modalidad_pago  # type: ignore[assignment]
        prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(  # type: ignore[assignment]
            prestamo.total_financiamiento, prestamo.modalidad_pago
        )

    # Aplicar cambios directos de numero_cuotas y cuota_periodo si se proporcionan
    if prestamo_data.numero_cuotas is not None:
        prestamo.numero_cuotas = prestamo_data.numero_cuotas  # type: ignore[assignment]

    if prestamo_data.cuota_periodo is not None:
        prestamo.cuota_periodo = prestamo_data.cuota_periodo  # type: ignore[assignment]

    if prestamo_data.tasa_interes is not None:
        prestamo.tasa_interes = prestamo_data.tasa_interes  # type: ignore[assignment]

    if prestamo_data.fecha_base_calculo is not None:
        prestamo.fecha_base_calculo = prestamo_data.fecha_base_calculo  # type: ignore[assignment]

    if prestamo_data.fecha_requerimiento is not None:
        prestamo.fecha_requerimiento = prestamo_data.fecha_requerimiento  # type: ignore[assignment]

    if prestamo_data.observaciones is not None:
        prestamo.observaciones = prestamo_data.observaciones  # type: ignore[assignment]

    if prestamo_data.usuario_proponente is not None:
        prestamo.usuario_proponente = prestamo_data.usuario_proponente  # type: ignore[assignment]

    if prestamo_data.analista is not None:
        prestamo.analista = prestamo_data.analista  # type: ignore[assignment]


def actualizar_monto_y_cuotas(prestamo: Prestamo, monto: Decimal):
    """Actualiza monto y recalcula cuotas"""
    prestamo.total_financiamiento = monto  # type: ignore[assignment]
    prestamo.numero_cuotas, prestamo.cuota_periodo = calcular_cuotas(prestamo.total_financiamiento, prestamo.modalidad_pago)  # type: ignore[assignment]


def procesar_cambio_estado(
    prestamo: Prestamo,
    nuevo_estado: str,
    current_user: User,
    db: Session,
    plazo_maximo_meses: Optional[int] = None,
    tasa_interes: Optional[Decimal] = None,
    fecha_base_calculo: Optional[date] = None,
):
    """Procesa el cambio de estado del préstamo"""
    estado_anterior = prestamo.estado
    prestamo.estado = nuevo_estado  # type: ignore[assignment]

    if nuevo_estado == "APROBADO":
        prestamo.usuario_aprobador = current_user.email  # type: ignore[assignment]
        prestamo.fecha_aprobacion = datetime.now()  # type: ignore[assignment]

        # Aplicar condiciones desde evaluación de riesgo (FASE 2)
        if plazo_maximo_meses:
            numero_cuotas, cuota_periodo = actualizar_cuotas_segun_plazo_maximo(prestamo, plazo_maximo_meses, db)
            logger.info(f"Cuotas ajustadas según análisis de riesgo: {numero_cuotas} cuotas")

        # Aplicar tasa de interés desde evaluación
        if tasa_interes:
            prestamo.tasa_interes = tasa_interes  # type: ignore[assignment]

        # Aplicar fecha base de cálculo
        if fecha_base_calculo:
            prestamo.fecha_base_calculo = fecha_base_calculo  # type: ignore[assignment]

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
    """Serializa un préstamo de forma segura, manejando campos que pueden no existir en BD o ser None"""
    return {
        "id": prestamo.id,
        "cliente_id": prestamo.cliente_id,
        "cedula": prestamo.cedula,
        "nombres": prestamo.nombres,
        "valor_activo": getattr(prestamo, "valor_activo", None),
        "total_financiamiento": prestamo.total_financiamiento,
        "fecha_requerimiento": prestamo.fecha_requerimiento,
        "modalidad_pago": prestamo.modalidad_pago,
        "numero_cuotas": prestamo.numero_cuotas,
        "cuota_periodo": prestamo.cuota_periodo,
        "tasa_interes": prestamo.tasa_interes,
        "fecha_base_calculo": getattr(prestamo, "fecha_base_calculo", None),
        "producto": prestamo.producto,
        "producto_financiero": prestamo.producto_financiero,
        "concesionario": getattr(prestamo, "concesionario", None),
        "analista": getattr(prestamo, "analista", None),
        "modelo_vehiculo": getattr(prestamo, "modelo_vehiculo", None),
        "estado": prestamo.estado,
        "usuario_proponente": prestamo.usuario_proponente,
        "usuario_aprobador": getattr(prestamo, "usuario_aprobador", None),
        "usuario_autoriza": getattr(prestamo, "usuario_autoriza", None),
        "observaciones": getattr(prestamo, "observaciones", None),
        "fecha_registro": prestamo.fecha_registro,
        "fecha_aprobacion": getattr(prestamo, "fecha_aprobacion", None),
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
            "valor_activo": getattr(row, "valor_activo", None),
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


@router.get("", response_model=dict)
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
        query = _aplicar_filtros_prestamos(
            query, search, estado, cedula, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

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

        # 1. Verificar que el cliente existe y está ACTIVO
        # Normalizar cédula (mayúsculas/sin espacios) para buscar y guardar
        cedula_norm = (prestamo_data.cedula or "").strip().upper()
        cliente = obtener_datos_cliente(cedula_norm, db)
        if not cliente:
            # Verificar si el cliente existe pero no está ACTIVO
            cliente_existente = db.query(Cliente).filter(Cliente.cedula == cedula_norm).first()
            if cliente_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El cliente con cédula {prestamo_data.cedula} tiene estado '{cliente_existente.estado}'. Solo se pueden crear préstamos para clientes con estado ACTIVO.",
                )
            raise HTTPException(
                status_code=404,
                detail=f"Cliente con cédula {prestamo_data.cedula} no encontrado",
            )

        # 2. Validar modelo de vehículo si viene y debe tener precio configurado
        valor_activo = None
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
            # Obtener el valor activo del modelo de vehículo
            valor_activo = existente.precio

        # Si viene valor_activo en el request, usarlo (permite override manual)
        if hasattr(prestamo_data, "valor_activo") and prestamo_data.valor_activo is not None:
            valor_activo = prestamo_data.valor_activo

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
            valor_activo=Decimal(valor_activo) if valor_activo is not None else None,
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
    try:
        # Normalizar cédula (mayúsculas/sin espacios) para buscar
        cedula_norm = cedula.strip().upper()
        logger.info(f"Buscando préstamos por cédula: {cedula_norm} - Usuario: {current_user.email}")

        # Obtener préstamos completos (no solo columnas específicas)
        prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula_norm).all()

        # Serializar de forma segura
        prestamos_serializados = []
        for prestamo in prestamos:
            try:
                prestamo_data = serializar_prestamo(prestamo)
                prestamos_serializados.append(PrestamoResponse.model_validate(prestamo_data))
            except Exception as e:
                logger.error(f"Error serializando préstamo {prestamo.id}: {e}", exc_info=True)
                # Continuar con el siguiente préstamo en lugar de fallar completamente
                continue

        return prestamos_serializados
    except HTTPException:
        raise
    except (ProgrammingError, OperationalError) as db_error:
        error_str = str(db_error).lower()
        logger.error(f"Error de base de datos en buscar_prestamos_por_cedula: {db_error}", exc_info=True)
        
        # Detectar errores de esquema (columnas o tablas que no existen)
        if "does not exist" in error_str or "no such column" in error_str or "no such table" in error_str or "relation" in error_str:
            detail_msg = (
                f"Error de esquema de base de datos. "
                f"Es posible que falten migraciones. "
                f"Ejecuta: alembic upgrade head. "
                f"Error: {str(db_error)}"
            )
            raise HTTPException(status_code=500, detail=detail_msg)
        
        # Otros errores de base de datos
        raise HTTPException(
            status_code=500,
            detail=f"Error de conexión a la base de datos: {str(db_error)}"
        )
    except Exception as e:
        logger.error(f"Error inesperado en buscar_prestamos_por_cedula: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/cedula/{cedula}/resumen", response_model=dict)
def obtener_resumen_prestamos_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener resumen de préstamos del cliente: saldo, cuotas en mora, etc.

    ✅ OPTIMIZADO: Eliminado N+1 queries - Una sola query agregada para todas las cuotas
    """
    from app.models.amortizacion import Cuota

    prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()

    if not prestamos:
        return {"tiene_prestamos": False, "total_prestamos": 0, "prestamos": []}

    # ✅ OPTIMIZACIÓN: Una sola query para todas las cuotas de todos los préstamos
    prestamos_ids = [p.id for p in prestamos]
    hoy = date.today()

    # ✅ MONITOREO: Registrar inicio de query
    from app.utils.query_monitor import query_monitor

    query_start = time.time()

    # Query agregada con GROUP BY - elimina N+1 queries
    cuotas_agregadas = (
        db.query(
            Cuota.prestamo_id,
            func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora).label("saldo_pendiente"),
            func.sum(case((and_(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO"), 1), else_=0)).label(
                "cuotas_en_mora"
            ),
        )
        .filter(Cuota.prestamo_id.in_(prestamos_ids))
        .group_by(Cuota.prestamo_id)
        .all()
    )

    # ✅ MONITOREO: Registrar tiempo de query
    query_time = int((time.time() - query_start) * 1000)
    query_monitor.record_query(
        query_name="obtener_resumen_prestamos_cliente_cuotas", execution_time_ms=query_time, query_type="SELECT"
    )

    # ✅ ALERTA: Si la query es lenta
    if query_time >= 2000:
        logger.warning(f"⚠️ [ALERTA] Query cuotas agregadas lenta: {query_time}ms para {len(prestamos_ids)} préstamos")

    # Crear diccionario para lookup rápido
    cuotas_por_prestamo = {row.prestamo_id: row for row in cuotas_agregadas}

    # Procesar resultados
    resumen_prestamos = []
    total_saldo = Decimal("0.00")
    total_cuotas_mora = 0

    for prestamo in prestamos:
        datos = cuotas_por_prestamo.get(prestamo.id)
        saldo_pendiente = Decimal(str(datos.saldo_pendiente)) if datos else Decimal("0.00")
        cuotas_en_mora = int(datos.cuotas_en_mora) if datos else 0

        total_saldo += saldo_pendiente
        total_cuotas_mora += cuotas_en_mora

        resumen_prestamos.append(
            {
                "id": prestamo.id,
                # Usar producto como respaldo. Evitamos consultar modelo_vehiculo
                # ya que puede no existir físicamente en la tabla todavía.
                "modelo_vehiculo": prestamo.producto,
                "total_financiamiento": float(prestamo.total_financiamiento),
                "saldo_pendiente": float(saldo_pendiente),
                "cuotas_en_mora": cuotas_en_mora,
                "estado": prestamo.estado,
                "fecha_registro": (prestamo.fecha_registro.isoformat() if prestamo.fecha_registro else None),
            }
        )

    return {
        "tiene_prestamos": True,
        "total_prestamos": len(resumen_prestamos),
        "total_saldo_pendiente": float(total_saldo),
        "total_cuotas_mora": total_cuotas_mora,
        "prestamos": resumen_prestamos,
    }


@router.get("/auditoria/{prestamo_id}")
def obtener_auditoria_prestamo(
    prestamo_id: int = Path(..., gt=0, description="ID del préstamo"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial de auditoría de un préstamo con paginación
    """
    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    # Calcular paginación
    skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

    # Query base
    query = (
        db.query(PrestamoAuditoria)
        .filter(PrestamoAuditoria.prestamo_id == prestamo_id)
        .order_by(PrestamoAuditoria.fecha_cambio.desc())
    )

    # Contar total
    total = query.count()

    # Aplicar paginación
    auditorias = query.offset(skip).limit(limit).all()

    # Serializar resultados
    items = [
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

    return create_paginated_response(items=items, total=total, page=page, page_size=limit)


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

        # ✅ Invalidar caché de cobranzas si se actualizó analista o usuario_proponente
        # Estos cambios afectan los datos de cobranzas
        if prestamo_data.analista is not None or prestamo_data.usuario_proponente is not None:
            try:
                from app.core.cache import invalidate_cache
                invalidate_cache("cobranzas:")
                logger.debug(f"Cache invalidado para cobranzas después de actualizar analista/usuario_proponente del préstamo {prestamo_id}")
            except Exception as cache_error:
                logger.warning(f"Error invalidando cache: {cache_error}")

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
            # ✅ NUEVAS COLUMNAS: Morosidad calculada automáticamente
            "dias_morosidad": c.dias_morosidad if hasattr(c, "dias_morosidad") else 0,
            "monto_morosidad": float(c.monto_morosidad) if hasattr(c, "monto_morosidad") and c.monto_morosidad else 0.0,
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
    prestamo.numero_cuotas = numero_cuotas  # type: ignore[assignment]
    prestamo.cuota_periodo = cuota_periodo  # type: ignore[assignment]

    logger.info(
        f"Cuotas recalculadas para préstamo {prestamo.id}: "
        f"{numero_cuotas} cuotas de ${cuota_periodo} "
        f"(plazo_maximo={plazo_maximo_meses} meses)"
    )

    return numero_cuotas, cuota_periodo


def _calcular_edad_cliente(fecha_nacimiento: date) -> tuple[float, int, int]:
    """Calcula edad del cliente en años, años enteros y meses desde fecha de nacimiento"""
    hoy = date.today()
    años = hoy.year - fecha_nacimiento.year

    if hoy.month < fecha_nacimiento.month or (hoy.month == fecha_nacimiento.month and hoy.day < fecha_nacimiento.day):
        años -= 1

    if hoy.month >= fecha_nacimiento.month:
        meses = hoy.month - fecha_nacimiento.month
        if hoy.day < fecha_nacimiento.day:
            meses -= 1
    else:
        meses = (12 - fecha_nacimiento.month) + hoy.month
        if hoy.day < fecha_nacimiento.day:
            meses -= 1

    if meses >= 12:
        años += meses // 12
        meses = meses % 12

    edad_total = años + (meses / 12)
    return edad_total, años, meses


def _obtener_edad_desde_bd(prestamo: Prestamo, db: Session, datos_evaluacion: dict) -> None:
    """Obtiene y agrega la edad del cliente desde la base de datos a datos_evaluacion"""
    if "edad" in datos_evaluacion and datos_evaluacion["edad"]:
        return

    cliente = db.query(Cliente).filter(Cliente.cedula == prestamo.cedula).first()
    if cliente and cliente.fecha_nacimiento:
        edad_total, años, meses = _calcular_edad_cliente(cliente.fecha_nacimiento)
        datos_evaluacion["edad"] = edad_total
        datos_evaluacion["edad_años"] = años
        datos_evaluacion["edad_meses"] = meses
        logger.info(f"Edad calculada desde BD: {años} años y {meses} meses (fecha_nacimiento: {cliente.fecha_nacimiento})")
    else:
        datos_evaluacion["edad"] = 25.0
        datos_evaluacion["edad_años"] = 25
        datos_evaluacion["edad_meses"] = 0
        logger.warning(f"No se encontró fecha de nacimiento para cédula {prestamo.cedula}, usando valor por defecto")


def _preparar_datos_evaluacion(prestamo: Prestamo, datos_evaluacion: dict, db: Session) -> None:
    """Prepara los datos de evaluación agregando información del préstamo y cliente"""
    datos_evaluacion["prestamo_id"] = prestamo.id

    if "cuota_mensual" not in datos_evaluacion or not datos_evaluacion["cuota_mensual"]:
        datos_evaluacion["cuota_mensual"] = float(prestamo.cuota_periodo) if prestamo.cuota_periodo else 0

    _obtener_edad_desde_bd(prestamo, db, datos_evaluacion)


def _actualizar_estado_evaluado(prestamo: Prestamo, prestamo_id: int, db: Session) -> None:
    """Actualiza el estado del préstamo a EVALUADO si está en DRAFT o EN_REVISION"""
    if prestamo.estado in ["DRAFT", "EN_REVISION"]:
        prestamo.estado = "EVALUADO"  # type: ignore[assignment]
        db.commit()
        logger.info(f"Préstamo {prestamo_id} cambiado a estado EVALUADO después de evaluación de riesgo")


def _obtener_prediccion_ml(prestamo: Prestamo, datos_evaluacion: dict, db: Session) -> Optional[dict]:
    """
    Obtiene predicción de riesgo del modelo ML activo si está disponible.
    Retorna None si no hay modelo activo o hay error.
    """
    try:
        # Verificar si hay modelo ML activo
        modelo_activo = db.query(ModeloRiesgo).filter(ModeloRiesgo.activo.is_(True)).first()
        if not modelo_activo:
            logger.info("No hay modelo ML activo, omitiendo predicción ML")
            return None

        # Verificar que MLService esté disponible
        try:
            from app.services.ml_service import ML_SERVICE_AVAILABLE, MLService

            if not ML_SERVICE_AVAILABLE or MLService is None:
                logger.warning("MLService no disponible, omitiendo predicción ML")
                return None
        except ImportError:
            logger.warning("MLService no disponible (scikit-learn no instalado), omitiendo predicción ML")
            return None

        # Cargar modelo
        ml_service = MLService()
        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
            logger.warning(f"Error cargando modelo ML desde {modelo_activo.ruta_archivo}")
            return None

        # Obtener datos del cliente para la predicción
        cliente = prestamo.cliente
        if not cliente:
            logger.warning("No se encontró cliente para predicción ML")
            return None

        # Calcular edad
        edad = datos_evaluacion.get("edad", 0)
        if not edad and cliente.fecha_nacimiento:
            from datetime import date

            hoy = date.today()
            edad = (hoy - cliente.fecha_nacimiento).days // 365

        # Obtener préstamos previos del cliente
        prestamos_previos = (
            db.query(Prestamo)
            .filter(
                and_(
                    Prestamo.cliente_id == prestamo.cliente_id,
                    Prestamo.id < prestamo.id,
                )
            )
            .count()
        )

        # Calcular días desde último préstamo
        from datetime import date

        dias_ultimo_prestamo = 0
        if prestamos_previos > 0:
            ultimo_prestamo = (
                db.query(Prestamo)
                .filter(
                    and_(
                        Prestamo.cliente_id == prestamo.cliente_id,
                        Prestamo.id < prestamo.id,
                    )
                )
                .order_by(Prestamo.fecha_registro.desc())
                .first()
            )
            if ultimo_prestamo and ultimo_prestamo.fecha_registro:
                dias_ultimo_prestamo = (date.today() - ultimo_prestamo.fecha_registro.date()).days

        # Calcular historial de pagos (simplificado: porcentaje de préstamos pagados)
        from app.models.amortizacion import Cuota
        from app.models.pago import Pago

        total_pagado = 0
        total_debe = 0

        # Obtener todos los préstamos del cliente
        prestamos_cliente = db.query(Prestamo).filter(Prestamo.cliente_id == prestamo.cliente_id).all()
        for p in prestamos_cliente:
            if p.total_financiamiento:
                total_debe += float(p.total_financiamiento)
            pagos = db.query(Pago).filter(Pago.prestamo_id == p.id).all()
            for pago in pagos:
                if pago.monto_pagado:
                    total_pagado += float(pago.monto_pagado)

        historial_pagos = total_pagado / total_debe if total_debe > 0 else 0.95  # Default si no hay historial

        # Calcular deuda total y ratio
        ingresos = float(datos_evaluacion.get("ingresos_mensuales", 0))
        otras_deudas = float(datos_evaluacion.get("otras_deudas", 0))
        deuda_total = otras_deudas + float(prestamo.total_financiamiento or 0)
        ratio_deuda_ingreso = deuda_total / ingresos if ingresos > 0 else 0

        # Preparar datos para predicción ML
        client_data = {
            "age": int(edad) if edad else 0,
            "income": ingresos,
            "debt_total": deuda_total,
            "debt_ratio": ratio_deuda_ingreso,
            "credit_score": historial_pagos,
            "dias_ultimo_prestamo": dias_ultimo_prestamo,
            "numero_prestamos_previos": prestamos_previos,
        }

        # Predecir
        prediccion = ml_service.predict_risk(client_data)

        logger.info(
            f"Predicción ML obtenida: Riesgo={prediccion.get('risk_level')}, "
            f"Confianza={prediccion.get('confidence', 0):.2%}"
        )

        return {
            "riesgo_level": prediccion.get("risk_level", "Desconocido"),
            "confidence": float(prediccion.get("confidence", 0)),
            "recommendation": prediccion.get("recommendation", ""),
            "features_used": prediccion.get("features_used", {}),
            "modelo_usado": {
                "nombre": modelo_activo.nombre,
                "version": modelo_activo.version,
                "algoritmo": modelo_activo.algoritmo,
                "accuracy": float(modelo_activo.accuracy) if modelo_activo.accuracy else None,
            },
        }
    except Exception as e:
        logger.error(f"Error obteniendo predicción ML: {e}", exc_info=True)
        return None


def _construir_respuesta_evaluacion(evaluacion, prestamo_id: int, prediccion_ml: Optional[dict] = None) -> dict:
    """Construye la respuesta completa de evaluación con todos los detalles"""
    respuesta = {
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
            "ratio_endeudamiento": {
                "puntos": float(evaluacion.ratio_endeudamiento_puntos or 0),
                "calculo": float(evaluacion.ratio_endeudamiento_calculo or 0),
            },
            "ratio_cobertura": {
                "puntos": float(evaluacion.ratio_cobertura_puntos or 0),
                "calculo": float(evaluacion.ratio_cobertura_calculo or 0),
            },
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
            "arraigo_vivienda": float(evaluacion.arraigo_vivienda_puntos or 0),
            "arraigo_familiar": float(evaluacion.arraigo_familiar_puntos or 0),
            "arraigo_laboral": float(evaluacion.arraigo_laboral_puntos or 0),
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
            "edad": {
                "puntos": float(evaluacion.edad_puntos or 0),
                "cliente": evaluacion.edad_cliente,
            },
            "capacidad_maniobra": {
                "puntos": float(evaluacion.enganche_garantias_puntos or 0),
                "porcentaje_residual": float(evaluacion.enganche_garantias_calculo or 0),
            },
        },
    }

    # Agregar predicción ML si está disponible
    if prediccion_ml:
        respuesta["prediccion_ml"] = prediccion_ml

    return respuesta


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

    _preparar_datos_evaluacion(prestamo, datos_evaluacion, db)

    logger.info(
        f"Evaluando préstamo {prestamo_id} con cuota: {datos_evaluacion['cuota_mensual']} USD, "
        f"edad: {datos_evaluacion.get('edad', 'N/A')} años"
    )

    try:
        evaluacion = crear_evaluacion_prestamo(datos_evaluacion, db)
        _actualizar_estado_evaluado(prestamo, prestamo_id, db)

        # Obtener predicción ML si hay modelo activo
        prediccion_ml = _obtener_prediccion_ml(prestamo, datos_evaluacion, db)

        if evaluacion.decision_final == "APROBADO_AUTOMATICO":
            logger.info(
                f"Préstamo {prestamo_id} es candidato para aprobación "
                f"(Riesgo: {evaluacion.clasificacion_riesgo}, Puntuación: {evaluacion.puntuacion_total}/100)"
            )
            logger.info(
                "⚠️ El sistema SUGIERE aprobar, pero requiere decisión humana. "
                "Usar endpoint '/aplicar-condiciones-aprobacion' para aprobar manualmente."
            )

        return _construir_respuesta_evaluacion(evaluacion, prestamo_id, prediccion_ml)

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
            prestamo.tasa_interes = Decimal(str(condiciones["tasa_interes"]))  # type: ignore[assignment]

        # Aplicar fecha base de cálculo (SI VIENE)
        if "fecha_base_calculo" in condiciones:
            fecha_str = condiciones["fecha_base_calculo"]
            prestamo.fecha_base_calculo = date_parse(fecha_str).date()  # type: ignore[assignment]

        # Aplicar observaciones
        if "observaciones" in condiciones:
            prestamo.observaciones = condiciones["observaciones"]  # type: ignore[assignment]

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
