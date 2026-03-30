"""Servicio de pagos alineado al modelo real `Pago` (tabla pagos).

La creacion de filas nuevas no se hace aqui: usar POST /pagos o flujos cobros/import.
Este modulo queda para lectura/ajustes puntuales y para `PagosValidacion` (duplicados, etc.).
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.prestamo import Prestamo

from .pagos_calculo import PagosCalculo
from .pagos_excepciones import PagoNotFoundError, PagoValidationError
from .pagos_validacion import PagosValidacion


class PagosService:
    def __init__(self, db: Session):
        self.db = db
        self.validacion = PagosValidacion(db)
        self.calculo = PagosCalculo(db)

    def crear_pago(self, datos_pago: dict) -> Pago:
        """
        Desactivado: el esquema antiguo (cliente_id, documento, etc.) no existe en `pagos`.

        Crear pagos: POST /pagos (autenticado) o import desde cobros / reportados.
        """
        raise PagoValidationError(
            "crear_pago",
            "La creacion de pagos debe hacerse por la API POST /pagos o por cobros/import; "
            "PagosService.crear_pago ya no aplica al modelo actual.",
        )

    def obtener_pago(self, pago_id: int) -> Pago:
        pago = self.db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise PagoNotFoundError(pago_id)
        return pago

    def obtener_pagos_cliente(self, cliente_id: int, limit: int = 100) -> List[Pago]:
        self.validacion.validar_cliente_existe(cliente_id)
        return (
            self.db.query(Pago)
            .join(Prestamo, Pago.prestamo_id == Prestamo.id)
            .filter(Prestamo.cliente_id == cliente_id)
            .order_by(desc(Pago.fecha_pago))
            .limit(limit)
            .all()
        )

    def actualizar_estado_pago(self, pago_id: int, nuevo_estado: str) -> Pago:
        pago = self.obtener_pago(pago_id)
        self.validacion.validar_estado_pago(nuevo_estado)
        pago.estado = nuevo_estado
        self.db.commit()
        self.db.refresh(pago)
        return pago

    def actualizar_pago(self, pago_id: int, datos_actualizacion: dict) -> Pago:
        pago = self.obtener_pago(pago_id)
        da = dict(datos_actualizacion)
        if "documento" in da:
            da["numero_documento"] = da.pop("documento")

        if "numero_documento" in da:
            nd = da["numero_documento"]
            nd_norm = normalize_documento(nd) if nd else None
            if nd_norm:
                self.validacion.validar_documento_no_duplicado(nd_norm, excluir_pago_id=pago_id)
            da["numero_documento"] = nd_norm

        campos_permitidos = ("monto_pagado", "estado", "numero_documento", "referencia_pago", "notas")

        for campo, valor in da.items():
            if campo not in campos_permitidos or valor is None:
                continue
            if campo == "monto_pagado":
                valor = self.validacion.validar_monto_numerico(float(valor))
                setattr(pago, campo, Decimal(str(round(valor, 2))))
            elif campo == "estado":
                self.validacion.validar_estado_pago(valor)
                setattr(pago, campo, valor)
            else:
                setattr(pago, campo, valor)

        self.db.commit()
        self.db.refresh(pago)
        return pago

    def eliminar_pago(self, pago_id: int) -> bool:
        pago = self.obtener_pago(pago_id)
        self.db.delete(pago)
        self.db.commit()
        return True

    def obtener_resumen_pagos(self, cliente_id: Optional[int] = None) -> dict:
        q = self.db.query(Pago)
        if cliente_id is not None:
            self.validacion.validar_cliente_existe(cliente_id)
            q = q.join(Prestamo, Pago.prestamo_id == Prestamo.id).filter(Prestamo.cliente_id == cliente_id)

        total_pagos = q.count()
        total_monto = q.with_entities(func.coalesce(func.sum(Pago.monto_pagado), 0)).scalar() or 0
        monto_promedio = (float(total_monto) / total_pagos) if total_pagos else 0.0

        q_est = self.db.query(Pago.estado, func.count(Pago.id), func.sum(Pago.monto_pagado)).group_by(Pago.estado)
        if cliente_id is not None:
            q_est = q_est.join(Prestamo, Pago.prestamo_id == Prestamo.id).filter(Prestamo.cliente_id == cliente_id)
        estado_dict = {
            estado: {"cantidad": int(cant or 0), "total": float(total or 0)}
            for estado, cant, total in q_est.all()
        }

        return {
            "total_pagos": total_pagos,
            "total_monto": float(total_monto or 0),
            "monto_promedio": float(monto_promedio),
            "por_estado": estado_dict,
        }

    def validar_integridad_pagos(self, cliente_id: int) -> dict:
        self.validacion.validar_cliente_existe(cliente_id)
        pagos = self.obtener_pagos_cliente(cliente_id, limit=1000)
        anomalias: list[dict] = []

        for pago in pagos:
            nd = getattr(pago, "numero_documento", None)
            if nd:
                duplicados = (
                    self.db.query(Pago)
                    .filter(Pago.numero_documento == nd, Pago.id != pago.id)
                    .count()
                )
                if duplicados > 0:
                    anomalias.append(
                        {
                            "tipo": "documento_duplicado",
                            "pago_id": pago.id,
                            "documento": nd,
                            "cantidad_duplicados": duplicados,
                        }
                    )

            mp = getattr(pago, "monto_pagado", None)
            if mp is None or float(mp) <= 0:
                anomalias.append(
                    {
                        "tipo": "monto_invalido",
                        "pago_id": pago.id,
                        "monto": mp,
                    }
                )

        return {
            "cliente_id": cliente_id,
            "total_pagos": len(pagos),
            "total_anomalias": len(anomalias),
            "anomalias": anomalias,
        }
