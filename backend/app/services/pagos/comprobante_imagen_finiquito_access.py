# -*- coding: utf-8 -*-
"""
Autorización de lectura de `pago_comprobante_imagen` para el portal Finiquito (JWT scope=finiquito).

Solo se permite si el comprobante está vinculado a datos del mismo titular (cédula) que el usuario portal:
pagos_reportados.comprobante_imagen_id o enlaces en pagos.link_comprobante / documento_ruta.
"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.finiquito import FiniquitoUsuarioAcceso
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def comprobante_imagen_accesible_finiquito_portal(
    db: Session,
    imagen_id_hex: str,
    fu: FiniquitoUsuarioAcceso,
) -> bool:
    cid = (imagen_id_hex or "").strip().lower()
    if len(cid) != 32:
        return False
    portal = texto_cedula_comparable_bd(fu.cedula)
    if not portal:
        return False

    for pr in (
        db.query(PagoReportado)
        .filter(PagoReportado.comprobante_imagen_id == cid)
        .limit(200)
        .all()
    ):
        doc = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}"
        if texto_cedula_comparable_bd(doc) == portal:
            return True

    like = f"%{cid}%"
    for p in (
        db.query(Pago)
        .filter(
            or_(
                Pago.link_comprobante.ilike(like),
                Pago.documento_ruta.ilike(like),
            )
        )
        .limit(400)
        .all()
    ):
        if texto_cedula_comparable_bd(getattr(p, "cedula_cliente", None)) == portal:
            return True

    return False
