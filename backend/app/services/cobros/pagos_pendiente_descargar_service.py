"""
Servicio para exportar pagos aprobados pendientes a Excel y vaciar la tabla temporal.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.pago_reportado import PagoReportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar


def obtener_pagos_aprobados_pendientes(db: Session) -> List[PagoReportado]:
    """
    Obtiene los pagos reportados aprobados que están en la tabla temporal de descargas.
    Los ordena por fecha de creación (más antiguos primero).
    """
    subquery = select(PagoPendienteDescargar.pago_reportado_id)
    
    query = (
        select(PagoReportado)
        .where(
            PagoReportado.id.in_(subquery),
            PagoReportado.estado == "aprobado"
        )
        .order_by(PagoPendienteDescargar.created_at)
    )
    
    return db.execute(query).scalars().all()


def agregar_a_pendiente_descargar(db: Session, pago_reportado_id: int) -> bool:
    """
    Agrega un pago a la tabla temporal de descargas si aún no está.
    Retorna True si fue agregado, False si ya existía.
    """
    # Verificar si ya existe
    existe = db.execute(
        select(PagoPendienteDescargar).where(
            PagoPendienteDescargar.pago_reportado_id == pago_reportado_id
        )
    ).first()
    
    if existe:
        return False
    
    # Agregar nuevo registro
    nuevo = PagoPendienteDescargar(pago_reportado_id=pago_reportado_id)
    db.add(nuevo)
    db.commit()
    
    return True


def vaciar_tabla_pendiente_descargar(db: Session) -> int:
    """
    Elimina todos los registros de la tabla pagos_pendiente_descargar.
    Retorna la cantidad de registros eliminados.
    """
    query = select(PagoPendienteDescargar)
    registros = db.execute(query).scalars().all()
    cantidad = len(registros)
    
    for registro in registros:
        db.delete(registro)
    
    db.commit()
    
    return cantidad


def obtener_datos_excel(pagos: List[PagoReportado]) -> List[Dict[str, Any]]:
    """
    Convierte pagos a filas para exportar a Excel.
    Columnas: Cédula, Fecha, Comentario, Número de Documento
    """
    rows = []
    
    for pago in pagos:
        fecha_str = pago.fecha_pago.strftime("%d/%m/%Y") if pago.fecha_pago else ""
        cedula = f"{pago.tipo_cedula}{pago.numero_cedula}" if pago.tipo_cedula and pago.numero_cedula else pago.numero_cedula or ""
        
        rows.append({
            "Cedula": cedula,
            "Fecha": fecha_str,
            "Comentario": pago.observacion or "",
            "Numero de Documento": pago.numero_operacion or "",
        })
    
    return rows
