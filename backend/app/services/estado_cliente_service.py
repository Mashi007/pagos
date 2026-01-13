"""
Servicio para gestionar estados de clientes automáticamente según reglas de negocio.

Reglas de Negocio:
- Por defecto: Todos los clientes nuevos tienen estado 'ACTIVO'
- ACTIVO: Si tiene préstamo aprobado o cuotas pendientes, O tiene 3 o menos cuotas atrasadas sin pagar
- INACTIVO: Automático cuando tiene 4 o más cuotas atrasadas sin pagar (vencidas y con total_pagado < monto_cuota)
- ACTIVO: Si está al día o termina de pagar todas las cuotas (siempre permanece ACTIVO, no cambia a FINALIZADO)
"""

import logging
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def verificar_y_actualizar_estado_inactivo(db: Session, cedula: str) -> bool:
    """
    Verifica si un cliente debe cambiar a INACTIVO automáticamente.
    
    Reglas:
    - ACTIVO: Si tiene préstamo aprobado o cuotas pendientes, O tiene 3 o menos cuotas atrasadas sin pagar
    - INACTIVO: Cuando tiene 4 o más cuotas atrasadas sin pagar (vencidas y con total_pagado < monto_cuota)
    
    Args:
        db: Sesión de base de datos
        cedula: Cédula del cliente
        
    Returns:
        bool: True si se actualizó el estado, False en caso contrario
    """
    try:
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            logger.warning(f"Cliente con cédula {cedula} no encontrado")
            return False
        
        # Obtener préstamos aprobados del cliente
        prestamos_ids = (
            db.query(Prestamo.id)
            .filter(Prestamo.cedula == cedula, Prestamo.estado == "APROBADO")
            .all()
        )
        prestamos_ids = [p[0] for p in prestamos_ids]
        
        if not prestamos_ids:
            # Si no tiene préstamos aprobados, mantener ACTIVO (regla por defecto)
            if cliente.estado != "ACTIVO":
                cliente.estado = "ACTIVO"
                db.commit()
                logger.info(f"Cliente {cedula} actualizado a ACTIVO (sin préstamos aprobados)")
                return True
            return False
        
        # Contar cuotas atrasadas sin pagar (vencidas y con total_pagado < monto_cuota)
        hoy = date.today()
        cuotas_atrasadas_sin_pagar = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.id.in_(prestamos_ids),
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,  # Vencida
                Cuota.total_pagado < Cuota.monto_cuota,  # Sin pagar completamente
            )
            .scalar()
            or 0
        )
        
        # Aplicar reglas
        if cuotas_atrasadas_sin_pagar >= 4:
            # Cambiar a INACTIVO si tiene 4 o más cuotas atrasadas sin pagar
            if cliente.estado != "INACTIVO":
                estado_anterior = cliente.estado
                cliente.estado = "INACTIVO"
                db.commit()
                logger.info(
                    f"Cliente {cedula} cambiado de {estado_anterior} a INACTIVO "
                    f"({cuotas_atrasadas_sin_pagar} cuotas atrasadas sin pagar)"
                )
                return True
        else:
            # Cambiar a ACTIVO si tiene 3 o menos cuotas atrasadas sin pagar
            # (o tiene préstamo aprobado o cuotas pendientes)
            if cliente.estado != "ACTIVO":
                estado_anterior = cliente.estado
                cliente.estado = "ACTIVO"
                db.commit()
                logger.info(
                    f"Cliente {cedula} cambiado de {estado_anterior} a ACTIVO "
                    f"({cuotas_atrasadas_sin_pagar} cuotas atrasadas sin pagar - 3 o menos)"
                )
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error verificando estado INACTIVO del cliente {cedula}: {e}", exc_info=True)
        db.rollback()
        return False


def actualizar_estado_cliente_por_prestamo(db: Session, cedula: str, estado_prestamo: str) -> bool:
    """
    Actualiza el estado del cliente según el estado del préstamo.
    
    Reglas:
    - Si préstamo es APROBADO: Cliente debe estar ACTIVO
    - Si préstamo es RECHAZADO: Verificar si debe cambiar a INACTIVO (solo si no tiene otros préstamos aprobados)
    
    Args:
        db: Sesión de base de datos
        cedula: Cédula del cliente
        estado_prestamo: Estado del préstamo (APROBADO, RECHAZADO, etc.)
        
    Returns:
        bool: True si se actualizó el estado, False en caso contrario
    """
    try:
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            logger.warning(f"Cliente con cédula {cedula} no encontrado")
            return False
        
        if estado_prestamo == "APROBADO":
            # Al aprobar préstamo, cliente debe estar ACTIVO
            if cliente.estado != "ACTIVO":
                cliente.estado = "ACTIVO"
                db.commit()
                logger.info(f"Cliente {cedula} actualizado a ACTIVO (préstamo aprobado)")
                return True
        
        elif estado_prestamo == "RECHAZADO":
            # Verificar si tiene otros préstamos aprobados
            otros_prestamos_aprobados = (
                db.query(func.count(Prestamo.id))
                .filter(Prestamo.cedula == cedula, Prestamo.estado == "APROBADO")
                .scalar()
                or 0
            )
            
            # Solo cambiar a INACTIVO si no tiene otros préstamos aprobados
            if otros_prestamos_aprobados == 0:
                # Verificar cuotas sin pagar antes de cambiar
                verificar_y_actualizar_estado_inactivo(db, cedula)
            else:
                # Mantener ACTIVO si tiene otros préstamos aprobados
                if cliente.estado != "ACTIVO":
                    cliente.estado = "ACTIVO"
                    db.commit()
                    logger.info(
                        f"Cliente {cedula} mantenido en ACTIVO "
                        f"(tiene {otros_prestamos_aprobados} otros préstamos aprobados)"
                    )
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error actualizando estado del cliente {cedula} por préstamo: {e}", exc_info=True)
        db.rollback()
        return False


def verificar_y_actualizar_estado_finalizado(db: Session, cedula: str) -> bool:
    """
    NOTA: Esta función ya no cambia a FINALIZADO.
    Según las nuevas reglas, los clientes siempre permanecen ACTIVO si están al día.
    
    Esta función ahora solo verifica si debe cambiar a INACTIVO por cuotas sin pagar.
    
    Args:
        db: Sesión de base de datos
        cedula: Cédula del cliente
        
    Returns:
        bool: True si se actualizó el estado, False en caso contrario
    """
    # Solo verificar estado INACTIVO según nuevas reglas
    return verificar_y_actualizar_estado_inactivo(db, cedula)
