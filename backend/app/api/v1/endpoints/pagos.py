"""
Endpoints para el módulo de Pagos
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.pago_auditoria import PagoAuditoria
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.pago import PagoCreate, PagoResponse, PagoUpdate
from app.utils.filtros_dashboard import FiltrosDashboard

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=dict)
def listar_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    analista: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar pagos con filtros y paginación
    """
    try:
        logger.info(
            f"📋 [listar_pagos] Iniciando consulta - página {page}, por página {per_page}"
        )

        # Verificar conexión a BD
        try:
            test_query = db.query(func.count(Pago.id)).scalar()
            logger.info(
                f"✅ [listar_pagos] Conexión BD OK. Total pagos en BD: {test_query}"
            )
        except Exception as db_error:
            logger.error(
                f"❌ [listar_pagos] Error de conexión BD: {db_error}", exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error de conexión a la base de datos: {str(db_error)}",
            )

        query = db.query(Pago)

        # Filtros
        if cedula:
            query = query.filter(Pago.cedula_cliente == cedula)
            logger.info(f"🔍 [listar_pagos] Filtro cédula: {cedula}")
        if estado:
            query = query.filter(Pago.estado == estado)
            logger.info(f"🔍 [listar_pagos] Filtro estado: {estado}")
        if fecha_desde:
            query = query.filter(Pago.fecha_pago >= fecha_desde)
            logger.info(f"🔍 [listar_pagos] Filtro fecha_desde: {fecha_desde}")
        if fecha_hasta:
            query = query.filter(Pago.fecha_pago <= fecha_hasta)
            logger.info(f"🔍 [listar_pagos] Filtro fecha_hasta: {fecha_hasta}")
        if analista:
            query = query.join(Prestamo).filter(Prestamo.usuario_proponente == analista)
            logger.info(f"🔍 [listar_pagos] Filtro analista: {analista}")

        # Contar total antes de aplicar paginación
        total = query.count()
        logger.info(
            f"📊 [listar_pagos] Total pagos encontrados (sin paginación): {total}"
        )

        # Ordenar por fecha de registro descendente (más actual primero)
        # Si hay misma fecha_registro, ordenar por ID descendente como criterio secundario
        query = query.order_by(Pago.fecha_registro.desc(), Pago.id.desc())

        # Paginación
        offset = (page - 1) * per_page
        pagos = query.offset(offset).limit(per_page).all()
        logger.info(f"📄 [listar_pagos] Pagos obtenidos de BD: {len(pagos)}")

        # Serializar pagos
        pagos_serializados = []
        errores_serializacion = 0
        hoy = date.today()

        for pago in pagos:
            try:
                # Convertir fecha_pago si es DATE a datetime si es necesario
                if hasattr(pago, "fecha_pago") and pago.fecha_pago is not None:
                    if isinstance(pago.fecha_pago, date) and not isinstance(
                        pago.fecha_pago, datetime
                    ):
                        # Si es date sin hora, convertir a datetime al inicio del día
                        pago.fecha_pago = datetime.combine(pago.fecha_pago, time.min)

                # Validar con el schema
                pago_dict = PagoResponse.model_validate(pago).model_dump()

                # ✅ Calcular cuotas atrasadas para este cliente
                # IMPORTANTE: Revisa TODAS las cuotas de TODOS los préstamos activos del cliente
                # Cuotas atrasadas = cuotas vencidas con pago incompleto (total_pagado < monto_cuota)
                cuotas_atrasadas = 0
                if pago.cedula_cliente:
                    # Obtener TODOS los préstamos APROBADOS del cliente (no solo del último pago)
                    prestamos_ids = [
                        p.id
                        for p in db.query(Prestamo.id)
                        .filter(
                            Prestamo.cedula == pago.cedula_cliente,
                            Prestamo.estado == "APROBADO",  # ✅ Solo préstamos activos
                        )
                        .all()
                    ]

                    if prestamos_ids:
                        # Contar TODAS las cuotas atrasadas de TODOS los préstamos del cliente
                        # Filtros aplicados:
                        # 1. Pertenece a algún préstamo del cliente
                        # 2. Está vencida (fecha_vencimiento < hoy)
                        # 3. No está completamente pagada (total_pagado < monto_cuota)
                        # ✅ NO HAY VALORES HARDCODEADOS - Todo se calcula dinámicamente desde la BD
                        cuotas_atrasadas_query = (
                            db.query(func.count(Cuota.id))
                            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                            .filter(
                                Prestamo.id.in_(prestamos_ids),
                                Prestamo.estado
                                == "APROBADO",  # ✅ Solo préstamos activos
                                Cuota.fecha_vencimiento < hoy,  # ✅ Vencida
                                Cuota.total_pagado
                                < Cuota.monto_cuota,  # ✅ Pago incompleto
                            )
                        )
                        cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

                        # Logging detallado para verificación (INFO para producción)
                        logger.info(
                            f"📊 [listar_pagos] Cliente {pago.cedula_cliente}: "
                            f"{len(prestamos_ids)} préstamos APROBADOS, "
                            f"{cuotas_atrasadas} cuotas atrasadas "
                            f"(fecha_vencimiento < {hoy} AND total_pagado < monto_cuota) - "
                            f"CÁLCULO DINÁMICO DESDE BD ✅"
                        )
                    else:
                        logger.debug(
                            f"📊 [listar_pagos] Cliente {pago.cedula_cliente}: Sin préstamos APROBADOS"
                        )
                else:
                    logger.debug(
                        f"📊 [listar_pagos] Pago ID {pago.id}: Sin cédula de cliente"
                    )

                # Agregar cuotas_atrasadas al diccionario
                pago_dict["cuotas_atrasadas"] = cuotas_atrasadas
                pagos_serializados.append(pago_dict)
            except Exception as serialization_error:
                errores_serializacion += 1
                # Log detallado del error y campos del pago
                error_detail = str(serialization_error)
                logger.error(
                    f"❌ [listar_pagos] Error serializando pago ID {pago.id}: {error_detail}",
                    exc_info=True,
                )
                logger.error(f"   Datos del pago: cedula={pago.cedula_cliente}")
                logger.error(
                    f"   fecha_pago={pago.fecha_pago} (tipo: {type(pago.fecha_pago)})"
                )
                logger.error(
                    f"   fecha_registro={getattr(pago, 'fecha_registro', 'N/A')} (tipo: {type(getattr(pago, 'fecha_registro', None))})"
                )
                logger.error(
                    f"   fecha_actualizacion={getattr(pago, 'fecha_actualizacion', 'N/A')} (tipo: {type(getattr(pago, 'fecha_actualizacion', None))})"
                )
                logger.error(
                    f"   fecha_conciliacion={getattr(pago, 'fecha_conciliacion', 'N/A')} (tipo: {type(getattr(pago, 'fecha_conciliacion', None))})"
                )
                # Continuar con los demás pagos, pero loguear el error
                continue

        if errores_serializacion > 0:
            logger.warning(
                f"⚠️ [listar_pagos] {errores_serializacion} de {len(pagos)} pagos fallaron en serialización"
            )

        logger.info(
            f"✅ [listar_pagos] Serializados exitosamente: {len(pagos_serializados)} pagos"
        )

        return {
            "pagos": pagos_serializados,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ [listar_pagos] Error general: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {error_msg}"
        )


@router.post("/", response_model=PagoResponse)
def crear_pago(
    pago_data: PagoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registrar un nuevo pago
    """
    try:
        # Verificar que el cliente existe
        cliente = (
            db.query(Cliente).filter(Cliente.cedula == pago_data.cedula_cliente).first()
        )
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Crear el pago
        pago_dict = pago_data.model_dump()
        pago_dict["usuario_registro"] = current_user.email
        pago_dict["fecha_registro"] = datetime.now()

        # Eliminar cualquier campo que no exista en el modelo (por ejemplo, referencia_pago si la migración no se ha ejecutado)
        campos_validos = [col.key for col in Pago.__table__.columns]
        pago_dict = {k: v for k, v in pago_dict.items() if k in campos_validos}

        nuevo_pago = Pago(**pago_dict)
        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)

        # Registrar auditoría
        registrar_auditoria_pago(
            pago_id=nuevo_pago.id,
            usuario=current_user.email,
            accion="CREATE",
            campo_modificado="pago_completo",
            valor_anterior="N/A",
            valor_nuevo=f"Pago de {pago_data.monto_pagado} registrado",
            db=db,
        )

        # Aplicar pago a cuotas
        cuotas_completadas = aplicar_pago_a_cuotas(nuevo_pago, db, current_user)

        # Actualizar estado del pago según regla de negocio:
        # - Si el pago no tiene préstamo asociado, mantener estado por defecto "PAGADO"
        # - Si tiene préstamo pero no completó ninguna cuota completamente → estado "PARCIAL" (abono parcial)
        # - Si completó al menos una cuota completamente → estado "PAGADO"
        if nuevo_pago.prestamo_id and cuotas_completadas == 0:
            nuevo_pago.estado = "PARCIAL"
        elif nuevo_pago.prestamo_id and cuotas_completadas > 0:
            nuevo_pago.estado = "PAGADO"
        # Si no tiene prestamo_id, mantener el estado por defecto "PAGADO"

        db.commit()
        db.refresh(nuevo_pago)

        return nuevo_pago
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en crear_pago: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{pago_id}", response_model=PagoResponse)
def actualizar_pago(
    pago_id: int,
    pago_data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualizar un pago existente
    """
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        # Registrar cambios para auditoría
        update_data = pago_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(pago, field):
                old_value = getattr(pago, field)
                setattr(pago, field, value)
                registrar_auditoria_pago(
                    pago_id=pago_id,
                    usuario=current_user.email,
                    accion="UPDATE",
                    campo_modificado=field,
                    valor_anterior=str(old_value) if old_value else "N/A",
                    valor_nuevo=str(value) if value else "N/A",
                    db=db,
                )

        pago.fecha_actualizacion = datetime.now()
        db.commit()
        db.refresh(pago)

        return pago
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_pago: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ============================================
# NUEVO: Listado de últimos pagos por cédula
# ============================================
@router.get("/ultimos", response_model=dict)
def listar_ultimos_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el último pago por cédula y métricas agregadas del balance general."""
    try:
        # Subconsulta: última fecha_registro por cédula
        sub_ultimos = (
            db.query(
                Pago.cedula_cliente.label("cedula"),
                func.max(Pago.fecha_registro).label("max_fecha"),
            )
            .group_by(Pago.cedula_cliente)
            .subquery()
        )

        # Join para obtener el registro de pago completo de esa última fecha
        pagos_ultimos_q = db.query(Pago).join(
            sub_ultimos,
            (Pago.cedula_cliente == sub_ultimos.c.cedula)
            & (Pago.fecha_registro == sub_ultimos.c.max_fecha),
        )

        # Filtros
        if cedula:
            pagos_ultimos_q = pagos_ultimos_q.filter(Pago.cedula_cliente == cedula)
        if estado:
            pagos_ultimos_q = pagos_ultimos_q.filter(Pago.estado == estado)

        # Total para paginación
        total = pagos_ultimos_q.count()

        # Paginación (ordenar por fecha_registro desc)
        offset = (page - 1) * per_page
        pagos_ultimos = (
            pagos_ultimos_q.order_by(Pago.fecha_registro.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        # Para cada cédula, calcular agregados sobre amortización (todas sus deudas)
        items = []
        from datetime import date
        from decimal import Decimal

        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        for pago in pagos_ultimos:
            # ✅ Obtener TODOS los préstamos APROBADOS del cliente (no solo del último pago)
            prestamos_ids = [
                p.id
                for p in db.query(Prestamo.id)
                .filter(
                    Prestamo.cedula == pago.cedula_cliente,
                    Prestamo.estado == "APROBADO",  # ✅ Solo préstamos activos
                )
                .all()
            ]

            total_prestamos = len(prestamos_ids)

            cuotas_atrasadas = 0
            saldo_vencido: Decimal = Decimal("0.00")
            if prestamos_ids:
                # ✅ IMPORTANTE: Contar TODAS las cuotas atrasadas de TODOS los préstamos activos del cliente
                # Reglas aplicadas:
                # 1. Pertenece a algún préstamo APROBADO del cliente
                # 2. fecha_vencimiento < hoy (vencida)
                # 3. total_pagado < monto_cuota (pago incompleto)
                # Esto incluye cuotas con estado ATRASADO, PARCIAL, PENDIENTE que estén vencidas e incompletas
                # NO solo las del último pago, sino TODAS las cuotas de la amortización de TODOS los préstamos
                # ✅ NO HAY VALORES HARDCODEADOS - Todo se calcula dinámicamente desde la BD
                hoy = date.today()
                cuotas_atrasadas_query = (
                    db.query(func.count(Cuota.id))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.id.in_(prestamos_ids),
                        Prestamo.estado == "APROBADO",  # ✅ Solo préstamos activos
                        Cuota.fecha_vencimiento < hoy,  # ✅ Vencida
                        Cuota.total_pagado
                        < Cuota.monto_cuota,  # ✅ Verificar que el pago NO esté completo
                    )
                )
                cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

                # Logging detallado para verificación
                logger.info(
                    f"📊 [ultimos_pagos] Cliente {pago.cedula_cliente}: "
                    f"{len(prestamos_ids)} préstamos APROBADOS, "
                    f"{cuotas_atrasadas} cuotas atrasadas "
                    f"(fecha_vencimiento < {hoy} AND total_pagado < monto_cuota) - "
                    f"TODAS las cuotas de TODOS los préstamos - CÁLCULO DINÁMICO DESDE BD ✅"
                )
                # Suma optimizada de saldos pendientes (capital+interes+mora) de todas las cuotas no pagadas
                # Usando func.sum para mejor performance
                saldo_result = (
                    db.query(
                        func.sum(
                            func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                            + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                            + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                        )
                    )
                    .filter(
                        Cuota.prestamo_id.in_(prestamos_ids),
                        Cuota.estado != "PAGADO",
                    )
                    .scalar()
                )
                saldo_vencido = saldo_result if saldo_result else Decimal("0.00")

            items.append(
                {
                    "cedula": pago.cedula_cliente,
                    "pago_id": pago.id,
                    "prestamo_id": pago.prestamo_id,
                    "estado_pago": pago.estado,
                    "monto_ultimo_pago": float(pago.monto_pagado),
                    "fecha_ultimo_pago": (
                        pago.fecha_pago.isoformat() if pago.fecha_pago else None
                    ),
                    "cuotas_atrasadas": int(cuotas_atrasadas),
                    "saldo_vencido": float(saldo_vencido),
                    "total_prestamos": total_prestamos,
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error en listar_ultimos_pagos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User) -> int:
    """
    Aplica un pago a las cuotas correspondientes según la regla de negocio:
    - Los pagos se aplican secuencialmente, cuota por cuota
    - Una cuota está "ATRASADO" hasta que esté completamente pagada (monto_cuota)
    - Solo cuando total_pagado >= monto_cuota, se marca como "PAGADO"
    - Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente

    Returns:
        int: Número de cuotas que se completaron completamente con este pago
    """
    if not pago.prestamo_id:
        return 0

    from datetime import date

    # Obtener TODAS las cuotas no pagadas del préstamo, ordenadas por número
    # (incluyendo PENDIENTE, ATRASADO, PARCIAL para aplicar pagos secuenciales)
    cuotas = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == pago.prestamo_id,
            Cuota.estado != "PAGADO",  # Solo cuotas no pagadas completamente
        )
        .order_by(Cuota.numero_cuota)
        .all()
    )

    saldo_restante = pago.monto_pagado
    cuotas_completadas = 0  # Contador de cuotas completadas con este pago

    for cuota in cuotas:
        if saldo_restante <= Decimal("0.00"):
            break

        # Calcular cuánto se puede aplicar a esta cuota (lo que falta para completarla)
        monto_faltante = cuota.monto_cuota - cuota.total_pagado
        monto_aplicar = min(saldo_restante, monto_faltante)

        # Si no hay nada que aplicar a esta cuota (ya está pagada), continuar con la siguiente
        if monto_aplicar <= Decimal("0.00"):
            continue

        # Actualizar montos pagados proporcionalmente (capital e interés)
        # Aplicar el pago proporcionalmente según lo que falta de capital e interés
        total_pendiente_cuota = cuota.capital_pendiente + cuota.interes_pendiente
        if total_pendiente_cuota > Decimal("0.00"):
            # Proporción según lo que falta pagar de cada uno
            capital_aplicar = monto_aplicar * (
                cuota.capital_pendiente / total_pendiente_cuota
            )
            interes_aplicar = monto_aplicar * (
                cuota.interes_pendiente / total_pendiente_cuota
            )
        else:
            # Si no hay pendiente (no debería pasar), aplicar todo al capital
            capital_aplicar = monto_aplicar
            interes_aplicar = Decimal("0.00")

        # Guardar estado previo ANTES de actualizar para detectar si se completó la cuota con este pago
        total_pagado_previo = cuota.total_pagado
        estado_previo_completo = total_pagado_previo >= cuota.monto_cuota

        # Actualizar cuota
        cuota.capital_pagado += capital_aplicar
        cuota.interes_pagado += interes_aplicar
        cuota.total_pagado += monto_aplicar
        cuota.capital_pendiente = max(
            Decimal("0.00"), cuota.capital_pendiente - capital_aplicar
        )
        cuota.interes_pendiente = max(
            Decimal("0.00"), cuota.interes_pendiente - interes_aplicar
        )

        # Actualizar fecha de pago solo si es el último pago recibido
        if monto_aplicar > Decimal("0.00"):
            cuota.fecha_pago = pago.fecha_pago

        # ACTUALIZAR ESTADO según la regla de negocio:
        # - Si la cuota está completamente pagada (total_pagado >= monto_cuota) → PAGADO
        # - Si tiene pago parcial pero NO está completa → ATRASADO (si vencida) o PENDIENTE (si no vencida)
        fecha_hoy = date.today()

        if cuota.total_pagado >= cuota.monto_cuota:
            # Cuota completamente pagada
            cuota.estado = "PAGADO"
            # Si antes NO estaba completa y ahora sí, incrementar contador
            if not estado_previo_completo:
                cuotas_completadas += 1
        elif cuota.total_pagado > Decimal("0.00"):
            # Cuota con pago parcial pero no completa
            # Si está vencida → ATRASADO, si no → PENDIENTE
            if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
                cuota.estado = "ATRASADO"
            else:
                cuota.estado = "PENDIENTE"
        else:
            # Cuota sin pago (no debería pasar, pero por seguridad)
            if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
                cuota.estado = "ATRASADO"
            else:
                cuota.estado = "PENDIENTE"

        saldo_restante -= monto_aplicar

    # Si queda saldo después de aplicar a todas las cuotas pendientes, es un pago adelantado
    # Aplicar el exceso a la siguiente cuota que esté PENDIENTE
    if saldo_restante > Decimal("0.00"):
        # Buscar la siguiente cuota pendiente (la primera que no esté pagada)
        siguiente_cuota = (
            db.query(Cuota)
            .filter(
                Cuota.prestamo_id == pago.prestamo_id,
                Cuota.estado != "PAGADO",
            )
            .order_by(Cuota.numero_cuota)
            .first()
        )

        if siguiente_cuota:
            # Aplicar el saldo restante a la siguiente cuota
            monto_faltante = siguiente_cuota.monto_cuota - siguiente_cuota.total_pagado
            monto_aplicar_exceso = min(saldo_restante, monto_faltante)

            if monto_aplicar_exceso > Decimal("0.00"):
                # Aplicar proporcionalmente según lo que falta de capital e interés
                total_pendiente_siguiente = (
                    siguiente_cuota.capital_pendiente
                    + siguiente_cuota.interes_pendiente
                )
                if total_pendiente_siguiente > Decimal("0.00"):
                    capital_exceso = monto_aplicar_exceso * (
                        siguiente_cuota.capital_pendiente / total_pendiente_siguiente
                    )
                    interes_exceso = monto_aplicar_exceso * (
                        siguiente_cuota.interes_pendiente / total_pendiente_siguiente
                    )
                else:
                    capital_exceso = monto_aplicar_exceso
                    interes_exceso = Decimal("0.00")

                # Guardar estado previo ANTES de actualizar para detectar si se completó la cuota
                total_pagado_previo_siguiente = siguiente_cuota.total_pagado
                estado_previo_siguiente_completo = (
                    total_pagado_previo_siguiente >= siguiente_cuota.monto_cuota
                )

                siguiente_cuota.capital_pagado += capital_exceso
                siguiente_cuota.interes_pagado += interes_exceso
                siguiente_cuota.total_pagado += monto_aplicar_exceso
                siguiente_cuota.capital_pendiente = max(
                    Decimal("0.00"), siguiente_cuota.capital_pendiente - capital_exceso
                )
                siguiente_cuota.interes_pendiente = max(
                    Decimal("0.00"), siguiente_cuota.interes_pendiente - interes_exceso
                )

                fecha_hoy = date.today()

                if siguiente_cuota.total_pagado >= siguiente_cuota.monto_cuota:
                    siguiente_cuota.estado = "PAGADO"
                    # Si antes NO estaba completa y ahora sí, incrementar contador
                    if not estado_previo_siguiente_completo:
                        cuotas_completadas += 1
                elif (
                    siguiente_cuota.fecha_vencimiento
                    and siguiente_cuota.fecha_vencimiento < fecha_hoy
                ):
                    siguiente_cuota.estado = "ATRASADO"
                else:
                    siguiente_cuota.estado = "ADELANTADO"

    db.commit()

    # Retornar número de cuotas completadas con este pago
    return cuotas_completadas


def registrar_auditoria_pago(
    pago_id: int,
    usuario: str,
    accion: str,
    campo_modificado: str,
    valor_anterior: str,
    valor_nuevo: str,
    observaciones: Optional[str] = None,
    db: Session = None,
):
    """
    Registra un cambio en la auditoría de pagos
    """
    auditoria = PagoAuditoria(
        pago_id=pago_id,
        usuario=usuario,
        campo_modificado=campo_modificado,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        accion=accion,
        observaciones=observaciones,
        fecha_cambio=datetime.now(),
    )
    db.add(auditoria)
    db.commit()


@router.get("/kpis")
def obtener_kpis_pagos(
    mes: Optional[int] = Query(None, description="Mes (1-12), default: mes actual"),
    año: Optional[int] = Query(None, description="Año, default: año actual"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs específicos para el módulo de Pagos

    Devuelve:
    - montoCobradoMes: Suma de todos los pagos del mes especificado
    - saldoPorCobrar: Suma de capital_pendiente + interes_pendiente + monto_mora de todas las cuotas no pagadas
    - clientesEnMora: Conteo de clientes únicos con cuotas vencidas y no pagadas
    - clientesAlDia: Conteo de clientes únicos sin cuotas vencidas sin pagar

    Los KPIs son fijos por mes (mes/año especificados o mes/año actual)
    """
    try:
        from datetime import date, datetime

        # Determinar mes y año (default: mes/año actual)
        hoy = date.today()
        mes_consulta = mes if mes is not None else hoy.month
        año_consulta = año if año is not None else hoy.year

        # Validar mes
        if mes_consulta < 1 or mes_consulta > 12:
            raise HTTPException(
                status_code=400, detail="El mes debe estar entre 1 y 12"
            )

        # Fecha inicio y fin del mes
        fecha_inicio_mes = date(año_consulta, mes_consulta, 1)
        # Calcular último día del mes
        if mes_consulta == 12:
            fecha_fin_mes = date(año_consulta + 1, 1, 1)
        else:
            fecha_fin_mes = date(año_consulta, mes_consulta + 1, 1)

        logger.info(
            f"📊 [kpis_pagos] Calculando KPIs para mes {mes_consulta}/{año_consulta}"
        )
        logger.info(
            f"📅 [kpis_pagos] Rango de fechas: {fecha_inicio_mes} a {fecha_fin_mes}"
        )

        # 1. MONTO COBRADO EN EL MES
        # Suma de todos los pagos del mes especificado (DATOS REALES DESDE BD)
        monto_cobrado_mes_query = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago >= datetime.combine(fecha_inicio_mes, datetime.min.time()),
            Pago.fecha_pago < datetime.combine(fecha_fin_mes, datetime.min.time()),
        )
        monto_cobrado_mes = monto_cobrado_mes_query.scalar() or Decimal("0.00")

        # Log detallado para verificación
        total_pagos_mes = (
            db.query(func.count(Pago.id))
            .filter(
                Pago.fecha_pago
                >= datetime.combine(fecha_inicio_mes, datetime.min.time()),
                Pago.fecha_pago < datetime.combine(fecha_fin_mes, datetime.min.time()),
            )
            .scalar()
            or 0
        )
        logger.info(
            f"💰 [kpis_pagos] Monto cobrado en el mes: ${monto_cobrado_mes:,.2f} (de {total_pagos_mes} pagos)"
        )

        # 2. SALDO POR COBRAR
        # Suma de capital_pendiente + interes_pendiente + monto_mora de todas las cuotas no pagadas (DATOS REALES DESDE BD)
        saldo_por_cobrar_query = (
            db.query(
                func.sum(
                    func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                )
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado != "PAGADO",
                Prestamo.estado == "APROBADO",
            )
        )
        saldo_por_cobrar = saldo_por_cobrar_query.scalar() or Decimal("0.00")

        # Log detallado para verificación
        total_cuotas_pendientes = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado != "PAGADO",
                Prestamo.estado == "APROBADO",
            )
            .scalar()
            or 0
        )
        logger.info(
            f"💳 [kpis_pagos] Saldo por cobrar: ${saldo_por_cobrar:,.2f} (de {total_cuotas_pendientes} cuotas pendientes)"
        )

        # 3. CLIENTES EN MORA
        # Clientes únicos con cuotas vencidas Y con pago incompleto (total_pagado < monto_cuota) (DATOS REALES DESDE BD)
        # Esto asegura que pagos parciales cuenten como mora si están vencidos

        # ✅ DIAGNÓSTICO: Verificar datos en BD antes del cálculo
        total_prestamos_aprobados = (
            db.query(func.count(Prestamo.id))
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0
        cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .filter(Cuota.fecha_vencimiento < hoy)
            .scalar()
            or 0
        )
        cuotas_pendientes = (
            db.query(func.count(Cuota.id)).filter(Cuota.estado != "PAGADO").scalar()
            or 0
        )
        
        # ✅ DIAGNÓSTICO ADICIONAL: Contar clientes únicos con préstamos aprobados
        clientes_unicos_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or 0
        )
        
        # ✅ DIAGNÓSTICO ADICIONAL: Contar préstamos aprobados CON cuotas generadas
        prestamos_con_cuotas = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or 0
        )
        
        # ✅ DIAGNÓSTICO ADICIONAL: Contar cuotas de préstamos aprobados
        cuotas_prestamos_aprobados = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or 0
        )
        
        logger.info(
            f"🔍 [kpis_pagos] DIAGNÓSTICO PRE-CÁLCULO: "
            f"Préstamos aprobados={total_prestamos_aprobados}, "
            f"Préstamos aprobados CON cuotas={prestamos_con_cuotas}, "
            f"Clientes únicos aprobados={clientes_unicos_aprobados}, "
            f"Total cuotas={total_cuotas}, "
            f"Cuotas de préstamos aprobados={cuotas_prestamos_aprobados}, "
            f"Cuotas vencidas={cuotas_vencidas}, "
            f"Cuotas pendientes={cuotas_pendientes}, "
            f"Fecha hoy={hoy}"
        )

        clientes_en_mora_query = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
                Prestamo.estado == "APROBADO",
            )
        )
        clientes_en_mora = clientes_en_mora_query.scalar() or 0

        # Log detallado para verificación
        cuotas_en_mora_count = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.estado == "APROBADO",
            )
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO ADICIONAL: Verificar si hay clientes con préstamos pero sin cuotas
        clientes_sin_cuotas = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .filter(
                Prestamo.estado == "APROBADO",
                ~Prestamo.id.in_(db.query(Cuota.prestamo_id).distinct()),
            )
            .scalar()
            or 0
        )
        
        # ✅ DIAGNÓSTICO ADICIONAL: Detalles de cuotas en mora
        # Obtener algunos ejemplos de cuotas en mora para verificación
        cuotas_mora_ejemplo = (
            db.query(Cuota.id, Cuota.prestamo_id, Cuota.fecha_vencimiento, Cuota.total_pagado, Cuota.monto_cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.estado == "APROBADO",
            )
            .limit(5)
            .all()
        )
        
        ejemplos_info = []
        for c in cuotas_mora_ejemplo:
            ejemplos_info.append(
                f"Cuota ID {c.id} (Préstamo {c.prestamo_id}): "
                f"Vencida {c.fecha_vencimiento}, "
                f"Pagado ${float(c.total_pagado):.2f} de ${float(c.monto_cuota):.2f}"
            )
        
        logger.info(
            f"⚠️ [kpis_pagos] Clientes en mora: {clientes_en_mora} "
            f"(con {cuotas_en_mora_count} cuotas vencidas e incompletas), "
            f"Clientes aprobados sin cuotas={clientes_sin_cuotas}"
        )
        
        if ejemplos_info:
            logger.info(
                f"📋 [kpis_pagos] Ejemplos de cuotas en mora ({min(len(ejemplos_info), 3)}): "
                + "; ".join(ejemplos_info[:3])
            )
        else:
            logger.info(
                f"✅ [kpis_pagos] No hay cuotas en mora detectadas (todas las cuotas están pagadas o no están vencidas)"
            )
        # 4. CLIENTES AL DÍA
        # Clientes únicos que tienen préstamos aprobados pero NO tienen cuotas vencidas sin pagar
        # Es decir: clientes con préstamos aprobados que no están en la lista de clientes en mora
        # O clientes que tienen todas sus cuotas vencidas pagadas o no tienen cuotas vencidas

        # Primero obtener todos los clientes con préstamos aprobados
        todos_clientes_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )

        # ✅ CÁLCULO MEJORADO: Clientes al día deben tener préstamos aprobados CON cuotas generadas
        # No contar clientes que tienen préstamos pero aún no tienen tabla de amortización
        clientes_con_cuotas = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )

        # Clientes al día = clientes con préstamos aprobados Y cuotas - clientes en mora
        # (Un cliente al día es uno que tiene préstamos aprobados con cuotas pero no está en mora)
        clientes_al_dia = max(0, clientes_con_cuotas - clientes_en_mora)

        logger.info(
            f"✅ [kpis_pagos] Clientes al día: {clientes_al_dia} "
            f"(de {clientes_con_cuotas} clientes con cuotas, "
            f"{todos_clientes_aprobados} totales aprobados, "
            f"{clientes_en_mora} en mora)"
        )
        return {
            "montoCobradoMes": float(monto_cobrado_mes),
            "saldoPorCobrar": float(saldo_por_cobrar),
            "clientesEnMora": clientes_en_mora,
            "clientesAlDia": clientes_al_dia,
            "mes": mes_consulta,
            "año": año_consulta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [kpis_pagos] Error obteniendo KPIs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error interno al obtener KPIs: {str(e)}"
        )


@router.get("/stats")
def obtener_estadisticas_pagos(
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de pagos con filtros opcionales
    """
    try:
        hoy = datetime.now().date()

        # ✅ Base query para pagos - usar FiltrosDashboard
        base_pago_query = db.query(Pago)
        if analista or concesionario or modelo:
            base_pago_query = base_pago_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
        base_pago_query = FiltrosDashboard.aplicar_filtros_pago(
            base_pago_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        # Total de pagos
        total_pagos = base_pago_query.count()

        # Pagos por estado (requiere subquery si hay filtros)
        pagos_por_estado_query = base_pago_query.subquery()
        if analista or concesionario or modelo:
            pagos_por_estado = (
                db.query(
                    pagos_por_estado_query.c.estado,
                    func.count(pagos_por_estado_query.c.id),
                )
                .group_by(pagos_por_estado_query.c.estado)
                .all()
            )
        else:
            pagos_por_estado = (
                db.query(Pago.estado, func.count(Pago.id)).group_by(Pago.estado).all()
            )

        # Monto total pagado
        total_pagado = base_pago_query.with_entities(
            func.sum(Pago.monto_pagado)
        ).scalar() or Decimal("0.00")

        # Pagos del día actual
        pagos_hoy_query = base_pago_query.filter(func.date(Pago.fecha_pago) == hoy)
        pagos_hoy = pagos_hoy_query.with_entities(
            func.sum(Pago.monto_pagado)
        ).scalar() or Decimal("0.00")

        # ✅ Cuotas pagadas vs pendientes - usar FiltrosDashboard
        cuotas_query = db.query(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        cuotas_pagadas = cuotas_query.filter(Cuota.estado == "PAGADO").count()
        cuotas_pendientes = cuotas_query.filter(Cuota.estado == "PENDIENTE").count()
        cuotas_atrasadas = cuotas_query.filter(Cuota.estado == "ATRASADO").count()

        return {
            "total_pagos": total_pagos,
            "pagos_por_estado": {estado: count for estado, count in pagos_por_estado},
            "total_pagado": float(total_pagado),
            "pagos_hoy": float(pagos_hoy),
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_pendientes": cuotas_pendientes,
            "cuotas_atrasadas": cuotas_atrasadas,
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/auditoria/{pago_id}", response_model=list[dict])
def obtener_auditoria_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial de auditoría de un pago
    """
    auditorias = (
        db.query(PagoAuditoria)
        .filter(PagoAuditoria.pago_id == pago_id)
        .order_by(PagoAuditoria.fecha_cambio.desc())
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
            "observaciones": a.observaciones,
            "fecha_cambio": a.fecha_cambio.isoformat(),
        }
        for a in auditorias
    ]
