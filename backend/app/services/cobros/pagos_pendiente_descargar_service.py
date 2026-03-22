"""
Servicio para exportar pagos aprobados pendientes a Excel y vaciar la tabla temporal.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.pago_reportado import PagoReportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar
from app.services.tasa_cambio_service import tasa_y_equivalente_usd_excel


def obtener_pagos_aprobados_pendientes(db: Session) -> List[PagoReportado]:
    """
    Obtiene los pagos reportados aprobados que están en la tabla temporal de descargas.
    Los ordena por fecha en que entraron a la cola (más antiguos primero).
    """
    query = (
        select(PagoReportado)
        .join(PagoPendienteDescargar, PagoPendienteDescargar.pago_reportado_id == PagoReportado.id)
        .where(PagoReportado.estado == "aprobado")
        .order_by(PagoPendienteDescargar.created_at.asc())
    )

    return db.execute(query).scalars().all()


def agregar_a_pendiente_descargar(db: Session, pago_reportado_id: int) -> bool:
    """
    Agrega un pago a la tabla temporal de descargas si aún no está.
    Retorna True si fue agregado, False si ya existía.

    No hace commit: el llamador debe confirmar la transacción (misma unidad que aprobar / crear pago).
    """
    existe = db.execute(
        select(PagoPendienteDescargar).where(
            PagoPendienteDescargar.pago_reportado_id == pago_reportado_id
        )
    ).scalars().first()

    if existe:
        return False

    db.add(PagoPendienteDescargar(pago_reportado_id=pago_reportado_id))
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


def obtener_datos_excel(db: Session, pagos: List[PagoReportado]) -> List[Dict[str, Any]]:
    """
    Convierte pagos a filas para exportar a Excel.
    Incluye tasa oficial Bs/USD (día fecha_pago) y equivalente en USD para pagos en Bs.
    """
    rows = []

    for pago in pagos:
        fecha_str = pago.fecha_pago.strftime("%d/%m/%Y") if pago.fecha_pago else ""
        cedula = (
            f"{pago.tipo_cedula}{pago.numero_cedula}"
            if pago.tipo_cedula and pago.numero_cedula
            else pago.numero_cedula or ""
        )
        monto_val = float(pago.monto) if pago.monto is not None else 0.0
        tasa_bs_usd, equiv_usd = (None, None)
        if pago.fecha_pago is not None:
            tasa_bs_usd, equiv_usd = tasa_y_equivalente_usd_excel(
                db, pago.fecha_pago, monto_val, pago.moneda
            )

        rows.append(
            {
                "Cedula": cedula,
                "Fecha": fecha_str,
                "Monto": monto_val,
                "Moneda": (pago.moneda or "BS").strip(),
                "Tasa cambio (Bs/USD)": tasa_bs_usd,
                "Bs a USD (equiv.)": equiv_usd,
                "Banco": (pago.institucion_financiera or "").strip(),
                "Comentario": pago.observacion or "",
                "Numero de Documento": pago.numero_operacion or "",
                # Última columna: referencia única en dólares (mismo valor que Bs a USD cuando aplica)
                "Monto en USD (solo dólares)": equiv_usd,
            }
        )

    return rows
