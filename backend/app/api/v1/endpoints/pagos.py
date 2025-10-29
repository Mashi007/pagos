"""
Endpoints para el módulo de Pagos
"""

import logging
from datetime import date, datetime
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
        query = db.query(Pago)

        # Filtros
        if cedula:
            query = query.filter(Pago.cedula_cliente == cedula)
        if estado:
            query = query.filter(Pago.estado == estado)
        if fecha_desde:
            query = query.filter(Pago.fecha_pago >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Pago.fecha_pago <= fecha_hasta)
        if analista:
            query = query.join(Prestamo).filter(Prestamo.usuario_proponente == analista)

        # Contar total antes de aplicar paginación
        total = query.count()

        # Ordenar por fecha de pago descendente
        query = query.order_by(Pago.fecha_pago.desc())

        # Paginación
        offset = (page - 1) * per_page
        pagos = query.offset(offset).limit(per_page).all()

        # Serializar pagos
        pagos_serializados = [
            PagoResponse.model_validate(pago).model_dump() for pago in pagos
        ]

        return {
            "pagos": pagos_serializados,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error en listar_pagos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


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
        aplicar_pago_a_cuotas(nuevo_pago, db, current_user)

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


def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User):
    """
    Aplica un pago a las cuotas correspondientes según la regla de negocio:
    - Los pagos se aplican secuencialmente, cuota por cuota
    - Una cuota está "ATRASADO" hasta que esté completamente pagada (monto_cuota)
    - Solo cuando total_pagado >= monto_cuota, se marca como "PAGADO"
    - Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente
    """
    if not pago.prestamo_id:
        return

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
                elif (
                    siguiente_cuota.fecha_vencimiento
                    and siguiente_cuota.fecha_vencimiento < fecha_hoy
                ):
                    siguiente_cuota.estado = "ATRASADO"
                else:
                    siguiente_cuota.estado = "ADELANTADO"

    db.commit()


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


@router.get("/stats")
def obtener_estadisticas_pagos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de pagos
    """
    try:
        # Total de pagos
        total_pagos = db.query(Pago).count()

        # Pagos por estado
        pagos_por_estado = (
            db.query(Pago.estado, func.count(Pago.id)).group_by(Pago.estado).all()
        )

        # Monto total pagado
        total_pagado = db.query(func.sum(Pago.monto_pagado)).scalar() or Decimal("0.00")

        # Pagos del día actual
        hoy = datetime.now().date()
        pagos_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) == hoy
        ).scalar() or Decimal("0.00")

        # Cuotas pagadas vs pendientes
        cuotas_pagadas = db.query(Cuota).filter(Cuota.estado == "PAGADO").count()
        cuotas_pendientes = db.query(Cuota).filter(Cuota.estado == "PENDIENTE").count()
        cuotas_atrasadas = db.query(Cuota).filter(Cuota.estado == "ATRASADO").count()

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
